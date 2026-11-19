from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage
from .state import MultiAgentState
from agents.config import CONVERSATIONAL_SYSTEM_PROMPT, get_chat_llm

# Só as últimas mensagens vão para o LLM, e cada uma (do usuário ou do assistente) é cortada.
MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_CHARS = 1500


def history_for_llm(messages: list[BaseMessage], limit: int = MAX_HISTORY_MESSAGES) -> list[BaseMessage]:
    history = [m for m in messages if hasattr(m, "content") and m.content and str(m.content).strip()]
    history = history[-limit:]
    trimmed = []
    for m in history:
        text = str(m.content)
        if len(text) > MAX_MESSAGE_CHARS:
            m = m.model_copy(update={"content": text[:MAX_MESSAGE_CHARS] + " […]"})
        trimmed.append(m)
    return trimmed


async def conversational_node(state: MultiAgentState):
    instruction = state.get("delegation_instruction") or state.get("user_input", "")

    history = history_for_llm(state.get("messages", []))

    if not history:
        history = [HumanMessage(content=instruction or "Olá!")]

    system_content = CONVERSATIONAL_SYSTEM_PROMPT.format(instruction=instruction)

    all_messages = [SystemMessage(content=system_content)] + history
    print(f"[Conversational] Recebidas {len(history)} msg(s) do histórico. Instrução: {instruction[:80]!r}")

    llm = get_chat_llm(temperature=0.0)
    response = await llm.ainvoke(all_messages)
    print(f"[Conversational] Resposta gerada ({len(response.text)} chars): {response.text[:120]!r}")

    # A resposta entra no histórico; sem isso o próximo turno vê as perguntas anteriores
    # como pendentes e responde de novo. Mesmo id da mensagem já transmitida por streaming.
    return {
        "messages": [AIMessage(content=response.text, id=response.id)],
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
