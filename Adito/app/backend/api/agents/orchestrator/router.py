from langchain_core.messages import SystemMessage, HumanMessage
from langchain_mistralai import ChatMistralAI
from .state import MultiAgentState
from .models import RouterDecision
from agents.config import ORCHESTRATOR_SYSTEM_PROMPT, MISTRAL_MODEL, MISTRAL_API_KEY

mcp_tools = []

llm = ChatMistralAI(model=MISTRAL_MODEL, api_key=MISTRAL_API_KEY, temperature=0.0)


async def orchestrator_node(state: MultiAgentState):
    global mcp_tools

    tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in mcp_tools]) if mcp_tools else "Nenhuma ferramenta externa disponível."
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(tools_desc=tools_desc)

    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")

    # Envia o histórico recente como contexto + a última mensagem como pergunta atual.
    # O orquestrador recebe contexto para resolver follow-ups ("E em 2025?", "E por vendedor?"),
    # mas o prompt instrui a rotear APENAS a última mensagem — nunca re-rotear perguntas antigas.
    all_messages = state.get("messages", [])
    context_messages = all_messages[:-1][-8:] if len(all_messages) > 1 else []
    current_message = all_messages[-1:] if all_messages else [HumanMessage(content=state.get("user_input", ""))]
    messages = [SystemMessage(content=system_prompt)] + context_messages + current_message
    decision: RouterDecision = await structured_llm.ainvoke(messages)

    calls_summary = [{"agente": c.intent, "instrução": c.delegation_instruction[:80]} for c in decision.calls]
    print(f"[Orchestrator] Roteamento → {calls_summary}")
    return {"calls": [c.model_dump() for c in decision.calls]}
