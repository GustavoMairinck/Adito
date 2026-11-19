import json
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.tools import tool

from analytics_index.config import TEXT_EMBEDDING_TOP_K
from analytics_index.services import configured_tables, search_text_embeddings
from core.records import Contexto
from core.rich_logging import log_info, log_success


@dataclass
class _Busca:
    """Estado de uma execução do resolvedor de valores."""

    contexto: Contexto
    embedder: Embeddings
    top_k: int = TEXT_EMBEDDING_TOP_K
    candidates: list[dict[str, Any]] = field(default_factory=list)
    searched_terms: list[str] = field(default_factory=list)
    search_calls: list[dict[str, Any]] = field(default_factory=list)


# Por execução, não global: duas perguntas ao mesmo tempo (threads diferentes) não se misturam.
# A ferramenta roda no mesmo contexto (o LangGraph copia o contexto para as threads das tools).
_busca: ContextVar[_Busca | None] = ContextVar("muninn_busca_valores", default=None)


def configure_vector_search(
    contexto: Contexto,
    embedder: Embeddings,
    top_k: int = TEXT_EMBEDDING_TOP_K,
) -> Token:
    """Liga a busca desta execução; devolva o token a `reset_vector_search` ao terminar."""
    return _busca.set(_Busca(contexto=contexto, embedder=embedder, top_k=top_k))


def reset_vector_search(token: Token) -> None:
    """Solta o contexto e o embedder da execução (não ficam presos ao contexto da thread)."""
    _busca.reset(token)


def vector_search_results() -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    busca = _busca.get()
    if busca is None:
        return [], [], []
    return busca.candidates, busca.searched_terms, busca.search_calls


@tool
def search_analytics_values(
    query: str,
    source_table: str = "",
    limit: int = TEXT_EMBEDDING_TOP_K,
) -> str:
    """Search real analytical text values by semantic similarity. source_table defaults to the first indexed view."""
    busca = _busca.get()
    if busca is None:
        return json.dumps({"query": query, "results": []}, ensure_ascii=False)

    tables = configured_tables(busca.contexto)
    clean_query = (query or "").strip()
    clean_table = (source_table or (tables[0] if tables else "")).strip()
    try:
        requested_limit = int(limit or busca.top_k)
    except (TypeError, ValueError):
        requested_limit = busca.top_k
    clean_limit = max(1, min(requested_limit, busca.top_k))

    if not clean_query:
        return json.dumps({"query": query, "results": []}, ensure_ascii=False)
    if clean_table not in tables:
        return json.dumps({"query": clean_query, "source_table": clean_table, "results": []}, ensure_ascii=False)

    log_info(
        "rewrite",
        f"tool search_analytics_values query={clean_query!r} table={clean_table!r} limit={clean_limit}",
    )
    query_embedding = busca.embedder.embed_query(clean_query)
    candidates = search_text_embeddings(
        contexto=busca.contexto,
        query_embedding=query_embedding,
        table=clean_table,
        top_k=clean_limit,
    )
    busca.searched_terms.append(clean_query)
    busca.candidates.extend(candidates)
    busca.search_calls.append(
        {
            "query": clean_query,
            "source_table": clean_table,
            "limit": clean_limit,
            "result_count": len(candidates),
            "best_distance": float(candidates[0]["distance"]) if candidates else None,
            "best_text": candidates[0]["embedding_text"][:220] if candidates else "",
        }
    )

    log_success(
        "rewrite",
        f"tool retornou {len(candidates)} candidato(s) para {clean_query!r}",
    )
    return json.dumps(
        {
            "query": clean_query,
            "source_table": clean_table,
            "results": candidates,
        },
        ensure_ascii=False,
        default=str,
    )
