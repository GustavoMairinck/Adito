from typing import Any

from langgraph.prebuilt import create_react_agent
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from analytics_index.config import TEXT_EMBEDDING_TOP_K
from analytics_index.services import configured_tables
from core.contexts import get_contexto
from core.rich_logging import (
    log_error,
    log_info,
    log_kv,
    log_node_end,
    log_node_start,
    log_table,
    log_warning,
)

from ..config import BI_VALUE_RESOLVER_SYSTEM_PROMPT, ValueResolverResponse
from ..state import BiAgentState
from ..tools.vector_search import (
    configure_vector_search,
    search_analytics_values,
    vector_search_results,
)


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

    configure_vector_search(contexto=contexto, embedder=embedder, top_k=top_k)

    try:
        agent = create_react_agent(
            model=llm_model,
            tools=[search_analytics_values],
            prompt=BI_VALUE_RESOLVER_SYSTEM_PROMPT,
            response_format=ValueResolverResponse,
        )
        result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
    except Exception as exc:
        log_error("rewrite", f"Falha no agente resolvedor de valores: {exc}")
        log_node_end("semantic_value_resolver", "falha; sem candidatos")
        return _empty_resolution()

    collected_candidates, searched_terms, search_calls = vector_search_results()
    structured = result.get("structured_response")
    if structured:
        searched_terms = searched_terms or list(structured.searched_terms)
        log_kv(
            "rewrite",
            "Resolvedor de valores",
            {
                "searched_terms": searched_terms,
                "tool_calls": search_calls,
                "reasoning": structured.reasoning,
            },
        )
    else:
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