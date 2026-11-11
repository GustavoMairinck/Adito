import json
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_mistralai import ChatMistralAI

from agents.config import MISTRAL_API_KEY, MISTRAL_MODEL
from core.rich_logging import log_error, log_info, log_warning

from ..config import (
    MAX_CHARS_TEXT,
    MAX_LOOP_ITERATIONS,
    MAX_ROWS_PER_ENTRY,
    MAX_TOTAL_CHARS,
    REFLECTION_DATA_PROMPT,
    CollectedDataEntry,
    ReflectionResult,
)
from ..state import MultiAgentState

llm = ChatMistralAI(model=MISTRAL_MODEL, api_key=MISTRAL_API_KEY, temperature=0.0)


def _as_entry(entry: CollectedDataEntry | dict) -> CollectedDataEntry:
    if isinstance(entry, CollectedDataEntry):
        return entry
    return CollectedDataEntry(**entry)


def _format_entry_full(entry: CollectedDataEntry | dict) -> str:
    entry = _as_entry(entry)
    parts = [f"### Consulta — {entry.tool_name} (iteração {entry.iteration})"]
    parts.append(f"**Instrução enviada:** {entry.instruction}")

    if entry.error:
        parts.append(f"**ERRO:** {entry.error}")
        return "\n".join(parts)

    if entry.sql_used:
        parts.append(f"**SQL:** `{entry.sql_used}`")

    if entry.text_response:
        text = entry.text_response[:MAX_CHARS_TEXT]
        if len(entry.text_response) > MAX_CHARS_TEXT:
            text += f"\n... [{len(entry.text_response) - MAX_CHARS_TEXT} caracteres omitidos]"
        parts.append(f"**Resposta:** {text}")

    if entry.data_rows:
        rows = entry.data_rows[:MAX_ROWS_PER_ENTRY]
        omitted = len(entry.data_rows) - len(rows)
        rows_json = json.dumps(rows, ensure_ascii=False, indent=2)
        parts.append(f"**Dados ({len(entry.data_rows)} linhas):**\n```\n{rows_json}\n```")
        if omitted > 0:
            parts.append(f"... {omitted} linhas omitidas")

    return "\n".join(parts)


def format_collected_data_for_reflection(collected: list[CollectedDataEntry | dict]) -> str:
    if not collected:
        return "Nenhum dado coletado ainda."

    full_blocks = [_format_entry_full(entry) for entry in reversed(collected)]
    full_text = "\n\n---\n\n".join(full_blocks)

    if len(full_text) <= MAX_TOTAL_CHARS:
        return full_text

    result_parts: list[str] = []
    total_chars = 0
    summary_parts: list[str] = []

    for entry in reversed(collected):
        block = _format_entry_full(entry)
        if total_chars + len(block) <= MAX_TOTAL_CHARS and not summary_parts:
            result_parts.append(block)
            total_chars += len(block)
            continue

        typed_entry = _as_entry(entry)
        if typed_entry.error:
            summary_parts.append(
                f"- [{typed_entry.tool_name} iter={typed_entry.iteration}] "
                f"ERRO: {typed_entry.error}"
            )
        else:
            n_rows = len(typed_entry.data_rows) if typed_entry.data_rows else 0
            summary_parts.append(
                f"- [{typed_entry.tool_name} iter={typed_entry.iteration}] "
                f"SQL: {(typed_entry.sql_used or 'N/A')[:80]} | "
                f"{n_rows} linhas | "
                f"Texto: {(typed_entry.text_response or '')[:100]}"
            )

    if summary_parts:
        result_parts.append(
            "### Entradas anteriores (resumidas por limite de contexto):\n"
            + "\n".join(summary_parts)
        )

    return "\n\n---\n\n".join(result_parts)


async def reflection_data_node(state: MultiAgentState) -> dict:
    iterations = state.get("iterations", 0)
    collected = state.get("collected_data", [])
    unresolvable = state.get("unresolvable_gaps", [])
    user_input = state.get("user_input", "")

    if iterations >= MAX_LOOP_ITERATIONS:
        log_warning(
            "reflection",
            f"MAX_ITERATIONS ({MAX_LOOP_ITERATIONS}) atingido. Forçando avanço com cobertura parcial.",
        )
        return {
            "forced_advance": True,
            "pending_gaps": [],
            "iterations": iterations,
        }

    schema_path = Path(__file__).resolve().parents[4] / "training" / "ddl" / "schema.sql"
    try:
        schema_str = schema_path.read_text(encoding="utf-8")
    except Exception as exc:
        log_warning("reflection", f"Schema indisponível em {schema_path}: {exc}")
        schema_str = "Esquema indisponível."

    prompt = REFLECTION_DATA_PROMPT.format(
        schema_str=schema_str,
        user_input=user_input,
        iteration=iterations,
        max_iterations=MAX_LOOP_ITERATIONS,
        collected_data_str=format_collected_data_for_reflection(collected),
        unresolvable_str="\n".join(f"- {gap}" for gap in unresolvable) or "Nenhuma.",
    )

    structured_llm = llm.with_structured_output(ReflectionResult, method="function_calling")
    try:
        result: ReflectionResult = await structured_llm.ainvoke([HumanMessage(content=prompt)])
    except Exception as exc:
        log_error("reflection", f"Erro ao invocar LLM: {exc}. Forçando avanço.")
        return {
            "forced_advance": True,
            "pending_gaps": [],
            "iterations": iterations + 1,
        }

    log_info(
        "reflection",
        (
            f"iter={iterations} | suficiente={result.suficiente} | "
            f"lacunas={result.lacunas} | unresolvable={result.unresolvable} | "
            f"raciocinio={result.raciocinio[:100]!r}"
        ),
    )

    return {
        "pending_gaps": result.lacunas if not result.suficiente else [],
        "unresolvable_gaps": list(set(unresolvable + result.unresolvable)),
        "forced_advance": False,
        "iterations": iterations + 1,
    }
