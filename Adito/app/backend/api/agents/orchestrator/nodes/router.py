from typing import Any, Sequence

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI

from agents.config import MISTRAL_API_KEY, MISTRAL_MODEL
from core.rich_logging import log_info, log_kv

from ..config import MAX_LOOP_ITERATIONS, ORCHESTRATOR_SYSTEM_PROMPT, RouterDecision
from ..state import _COLLECTED_RESET, MultiAgentState

llm = ChatMistralAI(model=MISTRAL_MODEL, api_key=MISTRAL_API_KEY, temperature=0.0)


def _entry_value(entry: dict | Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key)


def build_react_context(state: MultiAgentState) -> str:
    iterations = state.get("iterations", 0)
    pending_gaps = state.get("pending_gaps", [])
    unresolvable = state.get("unresolvable_gaps", [])
    collected = state.get("collected_data", [])

    instructions_made = "\n".join(
        f"  [{index + 1}] ({_entry_value(entry, 'tool_name')}) "
        f"{str(_entry_value(entry, 'instruction') or '')[:120]}"
        for index, entry in enumerate(collected)
    ) or "  Nenhuma ainda."

    gaps_str = "\n".join(f"  - {gap}" for gap in pending_gaps) or "  Nenhuma identificada ainda."
    unresolvable_str = "\n".join(f"  - {gap}" for gap in unresolvable) or "  Nenhuma."

    return f"""
=== CONTEXTO DO LOOP ReAct ===
Iteração atual: {iterations + 1} de {MAX_LOOP_ITERATIONS}

Consultas já realizadas (NÃO repita estas instruções):
{instructions_made}

Lacunas identificadas pela última Reflection (busque dados para estas):
{gaps_str}

Lacunas irresolúveis (o oráculo não encontrou estes dados — NÃO tente novamente):
{unresolvable_str}

Raciocine sobre o que ainda falta e instrua o agente de dados APENAS para as lacunas pendentes.
==============================
"""


async def run_orchestrator_node(
    state: MultiAgentState,
    tools: Sequence[Any],
) -> dict:
    tools_desc = (
        "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)
        if tools
        else "Nenhuma ferramenta externa disponível."
    )
    system_text = ORCHESTRATOR_SYSTEM_PROMPT.format(tools_desc=tools_desc)

    if state.get("report_loop_active"):
        system_text += build_react_context(state)

    raw_messages = state.get("messages", [])
    if state.get("report_loop_active") and state.get("iterations", 0) > 0:
        raw_messages = [
            message for message in raw_messages if isinstance(message, HumanMessage)
        ]

    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")
    decision: RouterDecision = await structured_llm.ainvoke(
        [SystemMessage(content=system_text)] + raw_messages
    )

    calls = [call.model_dump() for call in decision.calls]
    log_kv(
        "graph",
        "Roteamento do orquestrador",
        {
            "chamadas": [
                {
                    "agente": call["intent"],
                    "instrução": call["delegation_instruction"][:80],
                }
                for call in calls
            ]
        },
    )

    has_bi_agent = any(call["intent"] == "bi_agent" for call in calls)
    if (
        has_bi_agent
        and decision.requires_report
        and not state.get("report_loop_active", False)
    ):
        log_info("graph", "Novo ciclo BI detectado; resetando estado do loop.")
        return {
            "calls": calls,
            "report_loop_active": True,
            "iterations": 0,
            "collected_data": _COLLECTED_RESET,
            "pending_gaps": [],
            "unresolvable_gaps": [],
            "forced_advance": False,
        }

    return {"calls": calls}
