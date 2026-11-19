from langchain_core.messages import SystemMessage, HumanMessage
from .state import MultiAgentState
from .models import RouterDecision
from agents.config import ORCHESTRATOR_SYSTEM_PROMPT, get_chat_llm
from .guard import INTENT_BLOCKED, detect_injection
from .conversational_agent import history_for_llm

# Mensagens anteriores enviadas ao roteador como contexto (cortadas como no conversacional).
ROUTER_HISTORY_MESSAGES = 8

mcp_tools = []

async def orchestrator_node(state: MultiAgentState):
    global mcp_tools

    tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in mcp_tools]) if mcp_tools else "Nenhuma ferramenta externa disponível."
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(tools_desc=tools_desc)

    # Tentativa óbvia de prompt injection: bloqueia sem nem chamar o LLM.
    if detect_injection(state.get("user_input", "")):
        print("[Orchestrator] Prompt injection detectado pelo filtro; bloqueado sem LLM.")
        return {"calls": [{"intent": INTENT_BLOCKED, "delegation_instruction": ""}]}

    llm = get_chat_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")

    # Envia o histórico recente como contexto + a última mensagem como pergunta atual.
    # O orquestrador recebe contexto para resolver follow-ups ("E em 2025?", "E por campus?"),
    # mas o prompt instrui a rotear APENAS a última mensagem — nunca re-rotear perguntas antigas.
    all_messages = state.get("messages", [])
    context_messages = history_for_llm(all_messages[:-1], ROUTER_HISTORY_MESSAGES) if len(all_messages) > 1 else []
    current_message = all_messages[-1:] if all_messages else [HumanMessage(content=state.get("user_input", ""))]
    messages = [SystemMessage(content=system_prompt)] + context_messages + current_message
    decision: RouterDecision = await structured_llm.ainvoke(messages)

    calls_summary = [{"agente": c.intent, "instrução": c.delegation_instruction[:80]} for c in decision.calls]
    print(f"[Orchestrator] Roteamento → {calls_summary}")
    return {"calls": [c.model_dump() for c in decision.calls]}
