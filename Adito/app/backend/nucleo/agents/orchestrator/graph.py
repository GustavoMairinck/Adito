import asyncio
import json
import re
from contextlib import asynccontextmanager
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import AIMessage

from .state import MultiAgentState
from .router import orchestrator_node
from .conversational_agent import conversational_node
from .guard import GUARD_INTENTS, INTENT_BLOCKED, INTENT_OUT_OF_SCOPE, guard_node
from agents.config import checkpoint_db_path

mcp_tools = []


_compiled = None
_saver_cm = None
_path: str | None = None
_lock: asyncio.Lock | None = None


@asynccontextmanager
async def get_graph():
    """
    Grafo compilado com checkpointer SQLite (no app.db por padrão); o histórico fica isolado por thread_id.

    Compilado e conectado uma vez por processo (antes era a cada pergunta); reaberto se o caminho
    do banco mudar.
    """
    global _compiled, _saver_cm, _path, _lock
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        path = checkpoint_db_path()
        if _compiled is not None and _path != path:
            await _saver_cm.__aexit__(None, None, None)
            _compiled = _saver_cm = None
        if _compiled is None:
            saver_cm = AsyncSqliteSaver.from_conn_string(path)
            checkpointer = await saver_cm.__aenter__()
            await checkpointer.setup()
            _compiled, _saver_cm, _path = builder.compile(checkpointer=checkpointer), saver_cm, path
            print(f"[Graph] Compilado com checkpointer SQLite ({path}).")
    yield _compiled


async def close_graph():
    """Fecha a conexão do checkpointer ao encerrar o núcleo."""
    global _compiled, _saver_cm, _path, _lock
    if _saver_cm is not None:
        await _saver_cm.__aexit__(None, None, None)
    _compiled = _saver_cm = _path = _lock = None


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
                    "contexto_id": state.get("contexto_id", ""),
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


def merge_instructions(instrucoes: list[str]) -> str:
    """Junta várias instruções para a mesma ferramenta em um pedido só."""
    instrucoes = [i.strip() for i in instrucoes if i and i.strip()]
    if len(instrucoes) <= 1:
        return instrucoes[0] if instrucoes else ""
    itens = "\n".join(f"{n}. {i}" for n, i in enumerate(instrucoes, 1))
    return (
        "Responda todos os itens abaixo com uma única consulta SQL "
        "(use subconsultas, CTEs ou UNION ALL se precisar), com uma coluna identificando cada item:\n"
        + itens
    )


def route_from_orchestrator(state: MultiAgentState):
    calls = state.get("calls") or []
    intents = {call.get("intent") for call in calls}
    base = {
        "messages":              state.get("messages", []),
        "user_input":            state.get("user_input", ""),
        "tenant_id":             state.get("tenant_id"),
        "contexto_id":        state.get("contexto_id"),
        "thread_id":             state.get("thread_id"),
    }

    # Bloqueio vence tudo: nenhuma outra chamada roda junto.
    if INTENT_BLOCKED in intents:
        return [Send("guard_node", {**base, "tool_name": INTENT_BLOCKED})]

    tool_calls = [c for c in calls if c.get("intent") not in GUARD_INTENTS | {"conversational"}]
    if tool_calls:
        # Uma chamada por ferramenta: o estado guarda um resultado só (final_response, graph, sql_used),
        # então chamadas paralelas à mesma ferramenta se sobrescreviam e o usuário via só uma.
        por_ferramenta: dict[str, list[str]] = {}
        for c in tool_calls:
            por_ferramenta.setdefault(c.get("intent"), []).append(c.get("delegation_instruction") or "")
        return [
            Send("mcp_tool_node", {**base, "tool_name": nome,
                                   "delegation_instruction": merge_instructions(instrucoes)})
            for nome, instrucoes in por_ferramenta.items()
        ]
    if INTENT_OUT_OF_SCOPE in intents:
        return [Send("guard_node", {**base, "tool_name": INTENT_OUT_OF_SCOPE})]

    conversational = next((c for c in calls if c.get("intent") == "conversational"), {})
    return [Send("conversational_agent", {**base,
                 "delegation_instruction": conversational.get("delegation_instruction")})]


builder = StateGraph(MultiAgentState)
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("conversational_agent", conversational_node)
builder.add_node("mcp_tool_node", mcp_tool_node)
builder.add_node("guard_node", guard_node)
builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", route_from_orchestrator)
builder.add_edge("mcp_tool_node", END)
builder.add_edge("conversational_agent", END)
builder.add_edge("guard_node", END)
