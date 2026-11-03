import json
import re
from typing import Any, Sequence

from langchain_core.messages import AIMessage

from core.rich_logging import (
    log_error,
    log_info,
    log_kv,
    log_panel,
    log_success,
    log_table,
    log_warning,
)

from ..config import CollectedDataEntry
from ..state import MultiAgentState


def _entry_payload(**kwargs: Any) -> dict[str, Any]:
    return CollectedDataEntry(**kwargs).model_dump(mode="json")


def _tool_result_text(result: Any) -> str:
    if isinstance(result, list):
        return "".join(
            item.get("text", "")
            if isinstance(item, dict) and item.get("type") == "text"
            else getattr(item, "text", str(item))
            for item in result
        )

    content = getattr(result, "content", None)
    if isinstance(content, list):
        return "".join(getattr(item, "text", str(item)) for item in content)

    return str(result)


def _parse_json_content(content: str) -> dict[str, Any]:
    json_match = re.search(r"(\{.*\})", content, re.DOTALL)
    return json.loads(json_match.group(1)) if json_match else json.loads(content)


def _log_rewrite(instruction: str, rewrite: dict[str, Any]) -> None:
    log_kv(
        "rewrite",
        "Reescrita recebida do MCP",
        {
            "entrada_mcp": instruction,
            "buscas": rewrite.get("value_search_queries") or [],
            "tool_calls": rewrite.get("value_search_calls") or [],
            "pergunta_reescrita": rewrite.get("rewritten_user_input") or "",
            "motivo": rewrite.get("rewrite_reason") or "",
        },
    )
    candidates = rewrite.get("rewrite_candidates") or []
    if not candidates:
        return

    log_table(
        "rewrite",
        "Top-k semântico recebido no backend",
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


def _success_update(
    tool_name: str,
    instruction: str,
    iteration: int,
    parsed: dict[str, Any],
) -> dict[str, Any]:
    entry = _entry_payload(
        tool_name=tool_name,
        instruction=instruction,
        text_response=parsed.get("text_response"),
        sql_used=parsed.get("sql_used"),
        data_rows=parsed.get("data_rows"),
        field_formats=parsed.get("field_formats") or {},
        type=parsed.get("type"),
        score=parsed.get("score"),
        error=None,
        iteration=iteration,
    )
    return {
        "tool_name": tool_name,
        "collected_data": [entry],
        "messages": [AIMessage(content=f"[{tool_name}]:\n{parsed['final_content']}")],
        "final_response": parsed.get("text_response"),
        "text_response": parsed.get("text_response"),
        "analysis_explanation": parsed.get("text_response"),
        "sql_used": parsed.get("sql_used"),
        "graph": parsed.get("data_rows"),
        "field_formats": parsed.get("field_formats") or {},
        "type": parsed.get("type"),
        "score": parsed.get("score"),
        "message": parsed.get("message"),
        "suggestions": parsed.get("suggestions"),
        "related_attributes": parsed.get("related_attributes"),
        "rewrite": parsed.get("rewrite"),
    }


def _error_update(
    tool_name: str | None,
    instruction: str,
    iteration: int,
    message: str,
    content: str,
    entry_tool_name: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "collected_data": [
            _entry_payload(
                tool_name=entry_tool_name or tool_name or "unknown",
                instruction=instruction,
                error=message,
                iteration=iteration,
            )
        ],
        "messages": [AIMessage(content=content)],
    }


async def run_mcp_tool_node(
    state: MultiAgentState,
    tools: Sequence[Any],
) -> dict[str, Any]:
    tool_name = state.get("tool_name")
    instruction = state.get("delegation_instruction", "")
    iteration = state.get("iterations", 0)

    log_info("mcp", f"→ {tool_name} | iter={iteration} | instrução={instruction[:120]!r}")

    for tool in tools:
        if tool.name != tool_name:
            continue

        try:
            result = await tool.ainvoke(
                {
                    "instruction": instruction,
                    "tenant_id": state.get("tenant_id", ""),
                    "db_schema_name": state.get("db_schema_name", ""),
                    "thread_id": state.get("thread_id", "default_session"),
                }
            )
        except Exception as exc:
            log_error("mcp", f"← {tool_name} | erro: {exc}")
            return _error_update(
                tool_name=tool_name,
                instruction=instruction,
                iteration=iteration,
                message=str(exc),
                content=f"Erro na ferramenta {tool_name}: {exc}",
            )

        content = _tool_result_text(result) or str(result)
        try:
            parsed = _parse_json_content(content)
        except Exception as exc:
            log_warning(
                "mcp",
                f"← {tool_name} | parse JSON falhou: {exc} | raw={content[:120]!r}",
            )
            return _error_update(
                tool_name=tool_name,
                instruction=instruction,
                iteration=iteration,
                message=f"Parse JSON falhou: {content[:200]}",
                content=f"[{tool_name}]:\n{content}",
            )

        if not isinstance(parsed, dict) or "final_content" not in parsed:
            return _error_update(
                tool_name=tool_name,
                instruction=instruction,
                iteration=iteration,
                message=f"Parse JSON falhou: {content[:200]}",
                content=f"[{tool_name}]:\n{content}",
            )

        rewrite = parsed.get("rewrite") or {}
        if rewrite:
            _log_rewrite(instruction, rewrite)
        if parsed.get("sql_used"):
            log_panel("mcp", "SQL retornado pelo BI Agent", parsed.get("sql_used", ""))

        log_success(
            "mcp",
            (
                f"← {tool_name} | type={parsed.get('type')!r} "
                f"rows={len(parsed.get('data_rows') or [])} "
                f"field_formats={parsed.get('field_formats') or {}} "
                f"sql={parsed.get('sql_used', '')[:80]!r} "
                f"text={parsed.get('text_response', '')[:100]!r}"
            ),
        )

        return _success_update(tool_name, instruction, iteration, parsed)

    log_warning(
        "mcp",
        f"Ferramenta {tool_name!r} não encontrada. Disponíveis: {[tool.name for tool in tools]}",
    )
    return _error_update(
        tool_name=tool_name,
        instruction=instruction,
        iteration=iteration,
        message=f"Ferramenta MCP '{tool_name}' não encontrada.",
        content=f"Ferramenta MCP {tool_name} não encontrada.",
        entry_tool_name="unknown",
    )
