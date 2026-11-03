import json
import re
from contextlib import asynccontextmanager
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langchain_core.messages import AIMessage

from .state import MultiAgentState
from .router import orchestrator_node
from .conversational_agent import conversational_node
from agents.config import REDIS_URL, TTL_CONFIG

mcp_tools = []


@asynccontextmanager
async def get_graph():
    """
    Compila o grafo com Redis Checkpointer.
    O histórico de mensagens fica isolado por thread_id.
    """
    async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
        await _checkpointer.asetup()
        _graph = builder.compile(checkpointer=_checkpointer)
        print(f"[Graph] Compilado com Redis checkpointer ({REDIS_URL}).")
        yield _graph


async def mcp_tool_node(state: MultiAgentState):
    global mcp_tools
    tool_name   = state.get("tool_name")
    instruction = state.get("delegation_instruction", "")

    print(f"[MCP → {tool_name}] Instrução: {instruction[:100]!r}")

    for t in mcp_tools:
        if t.name == tool_name:
            try:
                invoke_args = {
                    "instruction":    instruction,
                    "tenant_id":      state.get("tenant_id", ""),
                    "db_schema_name": state.get("db_schema_name", ""),
                    "thread_id":      state.get("thread_id", "default_session"),
                }
                result = await t.ainvoke(invoke_args)

                content_str = ""
                def _safe_text(obj):
                    if isinstance(obj, dict) and obj.get("type") == "text":
                        return obj.get("text", "")
                    if hasattr(obj, "text"):
                        try:
                            return obj.text
                        except UnicodeDecodeError:
                            content = getattr(obj, "content", None)
                            if isinstance(content, (bytes, bytearray)):
                                return content.decode("latin-1", errors="replace")
                            return str(obj)
                    return str(obj)

                if isinstance(result, list):
                    parts = [_safe_text(r) for r in result]
                    content_str = "".join(parts)
                elif hasattr(result, "content") and isinstance(result.content, list):
                    content_str = "".join([_safe_text(c) for c in result.content])

                if not content_str:
                    content_str = str(result)

                try:
                    json_match = re.search(r'(\{.*\})', content_str, re.DOTALL)
                    parsed = json.loads(json_match.group(1)) if json_match else json.loads(content_str)

                    if isinstance(parsed, dict) and "final_content" in parsed:
                        print(f"[MCP ← {tool_name}] type={parsed.get('type')!r} | sql={parsed.get('sql_used','')[:60]!r} | rows={len(parsed.get('data_rows') or [])} | text={parsed.get('text_response','')[:100]!r}")
                        return {
                            "messages":           [AIMessage(content=f"[{tool_name}]:\n{parsed['final_content']}")],
                            "final_response":     parsed.get("text_response"),
                            "text_response":      parsed.get("text_response"),
                            "analysis_explanation": parsed.get("text_response"),
                            "sql_used":           parsed.get("sql_used"),
                            "graph":              parsed.get("data_rows"),
                            "type":               parsed.get("type"),
                            "score":              parsed.get("score"),
                            "message":            parsed.get("message"),
                            "suggestions":        parsed.get("suggestions"),
                            "related_attributes": parsed.get("related_attributes"),
                            "field_formats":      parsed.get("field_formats") or {},
                        }
                except Exception as parse_err:
                    print(f"[MCP ← {tool_name}] Parse JSON falhou: {parse_err} | raw={content_str[:120]!r}")

                return {"messages": [AIMessage(content=f"[{tool_name}]:\n{content_str}")]}

            except Exception as e:
                print(f"[MCP ← {tool_name}] ERRO: {e}")
                return {"messages": [AIMessage(content=f"Erro na ferramenta {tool_name}: {str(e)}")]}

    print(f"[MCP] Ferramenta {tool_name!r} não encontrada. Disponíveis: {[t.name for t in mcp_tools]}")
    return {"messages": [AIMessage(content=f"Ferramenta MCP {tool_name} não encontrada.")]}


def route_from_orchestrator(state: MultiAgentState):
    has_tool_calls = any(call.get("intent") != "conversational" for call in state["calls"])

    sends = []
    for call in state["calls"]:
        intent = call.get("intent")
        base = {
            "messages":              state.get("messages", []),
            "user_input":            state.get("user_input", ""),
            "tenant_id":             state.get("tenant_id"),
            "db_schema_name":        state.get("db_schema_name"),
            "thread_id":             state.get("thread_id"),
            "delegation_instruction": call.get("delegation_instruction"),
        }
        if intent == "conversational":
            if not has_tool_calls:
                sends.append(Send("conversational_agent", base))
        else:
            sends.append(Send("mcp_tool_node", {**base, "tool_name": intent}))
    return sends


builder = StateGraph(MultiAgentState)
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("conversational_agent", conversational_node)
builder.add_node("mcp_tool_node", mcp_tool_node)
builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", route_from_orchestrator)
builder.add_edge("mcp_tool_node", END)
builder.add_edge("conversational_agent", END)
