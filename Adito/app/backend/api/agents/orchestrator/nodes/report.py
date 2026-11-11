from langchain_core.messages import HumanMessage
from langchain_mistralai import ChatMistralAI

from agents.config import MISTRAL_API_KEY, MISTRAL_MODEL
from core.rich_logging import log_error, log_info, log_success

from ..config import REPORT_AGENT_PROMPT
from ..state import MultiAgentState
from .reflection import format_collected_data_for_reflection

llm = ChatMistralAI(model=MISTRAL_MODEL, api_key=MISTRAL_API_KEY, temperature=0.0)


async def report_agent_node(state: MultiAgentState) -> dict:
    collected = state.get("collected_data", [])
    forced_advance = state.get("forced_advance", False)
    unresolvable = state.get("unresolvable_gaps", [])
    user_input = state.get("user_input", "")

    warnings: list[str] = []
    if forced_advance:
        warnings.append(
            "**Aviso:** O número máximo de iterações foi atingido. "
            "Este relatório pode estar baseado em dados parciais."
        )
    if unresolvable:
        gaps_str = "\n".join(f"- {gap}" for gap in unresolvable)
        warnings.append(
            "**Dados indisponíveis:** As seguintes informações "
            f"não foram encontradas no banco:\n{gaps_str}"
        )

    prompt = REPORT_AGENT_PROMPT.format(
        user_input=user_input,
        n_entries=len(collected),
        data_str=format_collected_data_for_reflection(collected),
        partial_coverage="\n\n".join(warnings),
    )

    log_info(
        "report",
        (
            f"Gerando relatório com {len(collected)} entrada(s). "
            f"forced_advance={forced_advance} | unresolvable={unresolvable}"
        ),
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.text
    except Exception as exc:
        log_error("report", f"Erro ao invocar LLM: {exc}")
        content = (
            "Não foi possível gerar o relatório devido a um erro interno. "
            "Por favor, tente novamente."
        )

    log_success("report", f"Relatório gerado ({len(content)} chars): {content[:120]!r}")

    return {
        "final_response": content,
        "text_response": content,
        "analysis_explanation": content,
        "type": "report",
        "graph": None,
        "sql_used": None,
        "score": None,
        "message": None,
        "suggestions": [],
        "related_attributes": [],
        "report_loop_active": False,
        "forced_advance": False,
    }
