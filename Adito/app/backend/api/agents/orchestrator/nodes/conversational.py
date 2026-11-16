from langchain_core.messages import HumanMessage, SystemMessage

from agents.config import get_chat_llm
from core.rich_logging import log_info, log_success

from ..config import CONVERSATIONAL_SYSTEM_PROMPT
from ..state import MultiAgentState

async def conversational_node(state: MultiAgentState) -> dict:
    instruction = state.get("delegation_instruction") or state.get("user_input", "")

    raw_history = state.get("messages", [])
    history = [
        message
        for message in raw_history
        if hasattr(message, "content") and message.content and str(message.content).strip()
    ]

    if not history:
        history = [HumanMessage(content=instruction or "Olá!")]

    system_content = CONVERSATIONAL_SYSTEM_PROMPT.format(instruction=instruction)
    llm = get_chat_llm(temperature=0.0)
    response = await llm.ainvoke([SystemMessage(content=system_content)] + history)

    log_info(
        "graph",
        f"Conversacional recebeu {len(history)} msg(s). instrução={instruction[:100]!r}",
    )
    log_success(
        "graph",
        f"Resposta conversacional gerada ({len(response.text)} chars): {response.text[:120]!r}",
    )

    return {
        "final_response": response.text,
        "text_response": response.text,
        "analysis_explanation": None,
        "sql_used": None,
        "graph": None,
        "type": "chat",
        "score": None,
        "message": None,
        "suggestions": [],
        "related_attributes": [],
    }
