from typing import Any

from langgraph.prebuilt import create_react_agent
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from analytics_index.config import TEXT_EMBEDDING_TOP_K
from analytics_index.services import configured_tables
from core import db
from core.contexts import get_contexto
from core.db import to_db_id
from core.rich_logging import (
    log_error,
    log_info,
    log_kv,
    log_node_end,
    log_node_start,
    log_table,
    log_warning,
)

from ..config import BI_VALUE_RESOLVER_SYSTEM_PROMPT
from ..state import BiAgentState
from ..tools.vector_search import (
    configure_vector_search,
    reset_vector_search,
    search_analytics_values,
    vector_search_results,
)


def _indexed_tables_hint(contexto) -> str:
    """Lista views e colunas indexadas para o resolvedor escolher a `source_table` correta."""
    lines = []
    for view in getattr(contexto, "views", None) or []:
        name = view.get("name")
        cols = view.get("embed_columns") or []
        if name and cols:
            lines.append(f"- {name}: {', '.join(cols)}")
    if not lines:
        return ""
    return "\n\nAvailable indexed views (source_table -> embed_columns):\n" + "\n".join(lines)


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for candidate in candidates:
        key = (candidate.get("source_table"), candidate.get("embedding_text"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _last_message_content(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return ""
    return str(getattr(messages[-1], "content", "") or "")


def _empty_resolution() -> dict[str, list]:
    return {"rewrite_candidates": [], "value_search_queries": [], "value_search_calls": []}


def _has_indexed_values(contexto) -> bool:
    try:
        row = db.execute(
            "SELECT 1 FROM analytics_text_embedding WHERE contexto_id = ? AND embedding IS NOT NULL LIMIT 1",
            [to_db_id(contexto.id)],
        ).fetchone()
        return row is not None
    except Exception as exc:
        log_warning("rewrite", f"Falha ao verificar analytics_text_embedding ({exc}); pulando resolução de valores.")
        return False


def semantic_value_resolver(
    state: BiAgentState,
    llm_model: BaseChatModel,
    embedder: Embeddings,
    top_k: int = TEXT_EMBEDDING_TOP_K,
) -> dict[str, object]:
    user_input = state["user_input"]
    log_node_start("semantic_value_resolver", f"pergunta={user_input[:120]!r}")

    contexto = get_contexto(state.get("contexto_id"))
    if contexto is None or not configured_tables(contexto):
        log_warning("rewrite", "Contexto sem views indexadas (embed_columns); pulando resolução de valores.")
        log_node_end("semantic_value_resolver", "sem candidatos")
        return _empty_resolution()
    if not _has_indexed_values(contexto):
        log_info("rewrite", "Nenhum valor indexado em analytics_text_embedding; pulando resolução de valores.")
        log_node_end("semantic_value_resolver", "sem valores indexados")
        return _empty_resolution()

    prompt = BI_VALUE_RESOLVER_SYSTEM_PROMPT + _indexed_tables_hint(contexto)
    result: dict[str, Any] = {}
    token = configure_vector_search(contexto=contexto, embedder=embedder, top_k=top_k)
    try:
        try:
            # Sem response_format: o nó extra generate_structured_response do LangGraph envia
            # histórico terminando em AIMessage, rejeitado pelo Gemini ("does not support model prefilling").
            # Os candidatos e termos pesquisados já são coletados diretamente via vector_search_results().
            agent = create_react_agent(
                model=llm_model,
                tools=[search_analytics_values],
                prompt=prompt,
            )
            result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
        except Exception as exc:
            log_error("rewrite", f"Falha no agente resolvedor de valores: {exc}")
        collected_candidates, searched_terms, search_calls = vector_search_results()
    finally:
        reset_vector_search(token)

    if search_calls:
        log_kv(
            "rewrite",
            "Resolvedor de valores",
            {
                "searched_terms": searched_terms,
                "tool_calls": search_calls,
            },
        )
    elif result:
        log_info(
            "rewrite",
            f"Resolvedor de valores respondeu: {_last_message_content(result)[:240]!r}",
        )

    candidates = _dedupe_candidates(collected_candidates)
    if candidates:
        log_table(
            "rewrite",
            "Top-k semântico do resolvedor",
            ["#", "distância", "tabela", "texto embedado", "payload"],
            [
                [
                    index,
                    f"{candidate.get('distance', 0):.4f}",
                    candidate.get("source_table", ""),
                    candidate.get("embedding_text", "")[:260],
                    candidate.get("payload_json", ""),
                ]
                for index, candidate in enumerate(candidates, 1)
            ],
        )
    else:
        log_info(
            "rewrite",
            "Resolvedor não encontrou candidatos; rewriter usará a pergunta original.",
        )

    log_node_end("semantic_value_resolver", f"{len(candidates)} candidato(s)")
    return {
        "rewrite_candidates": candidates,
        "value_search_queries": searched_terms,
        "value_search_calls": search_calls,
    }