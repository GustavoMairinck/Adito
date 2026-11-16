from langchain_core.messages import SystemMessage, HumanMessage
from .state import MultiAgentState
from agents.config import CONVERSATIONAL_SYSTEM_PROMPT, get_chat_llm


async def conversational_node(state: MultiAgentState):
    instruction = state.get("delegation_instruction") or state.get("user_input", "")

    raw_history = state.get("messages", [])
    history = [m for m in raw_history if hasattr(m, "content") and m.content and str(m.content).strip()]

    if not history:
        history = [HumanMessage(content=instruction or "Olá!")]

    system_content = CONVERSATIONAL_SYSTEM_PROMPT.format(instruction=instruction)

    all_messages = [SystemMessage(content=system_content)] + history
    print(f"[Conversational] Recebidas {len(history)} msg(s) do histórico. Instrução: {instruction[:80]!r}")

    llm = get_chat_llm(temperature=0.0)
    response = await llm.ainvoke(all_messages)
    print(f"[Conversational] Resposta gerada ({len(response.text)} chars): {response.text[:120]!r}")

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
