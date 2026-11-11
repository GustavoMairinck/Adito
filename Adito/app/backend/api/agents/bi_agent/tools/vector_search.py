import json
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.tools import tool

from analytics_index.config import TEXT_EMBEDDING_TOP_K
from analytics_index.services import configured_tables, search_text_embeddings
from core.models import Contexto
from core.rich_logging import log_info, log_success


_contexto: Contexto | None = None
_embedder: Embeddings | None = None
_top_k: int = TEXT_EMBEDDING_TOP_K
_collected_candidates: list[dict[str, Any]] = []
_searched_terms: list[str] = []
_search_calls: list[dict[str, Any]] = []


def configure_vector_search(
    contexto: Contexto,
    embedder: Embeddings,
    top_k: int = TEXT_EMBEDDING_TOP_K,
) -> None:
    global _contexto, _embedder, _top_k, _collected_candidates, _searched_terms, _search_calls
    _contexto = contexto
    _embedder = embedder
    _top_k = top_k
    _collected_candidates = []
    _searched_terms = []
    _search_calls = []


def vector_search_results() -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    return _collected_candidates, _searched_terms, _search_calls


@tool
def search_analytics_values(
    query: str,
    source_table: str = "",
    limit: int = TEXT_EMBEDDING_TOP_K,
) -> str:
    """Search real analytical text values by semantic similarity. source_table defaults to the first indexed view."""
    if _contexto is None or _embedder is None:
        return json.dumps({"query": query, "results": []}, ensure_ascii=False)

    tables = configured_tables(_contexto)
    clean_query = (query or "").strip()
    clean_table = (source_table or (tables[0] if tables else "")).strip()
    try:
        requested_limit = int(limit or _top_k)
    except (TypeError, ValueError):
        requested_limit = _top_k
    clean_limit = max(1, min(requested_limit, _top_k))

    if not clean_query:
        return json.dumps({"query": query, "results": []}, ensure_ascii=False)
    if clean_table not in tables:
        return json.dumps({"query": clean_query, "source_table": clean_table, "results": []}, ensure_ascii=False)

    log_info(
        "rewrite",
        f"tool search_analytics_values query={clean_query!r} table={clean_table!r} limit={clean_limit}",
    )
    query_embedding = _embedder.embed_query(clean_query)
    candidates = search_text_embeddings(
        contexto=_contexto,
        query_embedding=query_embedding,
        table=clean_table,
        top_k=clean_limit,
    )
    _searched_terms.append(clean_query)
    _collected_candidates.extend(candidates)
    _search_calls.append(
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
