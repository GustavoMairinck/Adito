"""Chat: pergunta com streaming, histórico de conversas e reexecução do SQL das respostas."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal

from langchain_core.messages import HumanMessage

from agents.bi_agent.agent import execute_query
from agents.bi_agent.tool import local_tools
from agents.config import langfuse_callbacks
from agents.orchestrator.graph import get_graph
from core import db
from core.contexts import pick_contexto
from core.db import api_dt, to_db_id
from core.records import Conversation, Message, QueryExecution, delete_conversation
from core.rich_logging import log_info, log_section, log_success

from .core_methods import LLM_KEY_MISSING, llm_configured
from .errors import ApiError, not_found
from .registry import rpc
from .session import current

logger = logging.getLogger(__name__)


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, uuid.UUID)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _clean_explanation(value: str | None, answer: str) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned == answer or cleaned.startswith("[/"):
        return None
    return cleaned


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip() and not value.strip().startswith("[/"):
            return value.strip()
    return None


def _format_number_pt_br(value: object) -> str:
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return str(value)
    return f"{parsed:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _scalar_result_answer(data: list[dict]) -> str | None:
    if len(data) != 1 or len(data[0]) != 1:
        return None
    label, value = next(iter(data[0].items()))
    label_pt = str(label).replace("_", " ")
    return f"O {label_pt} é {_format_number_pt_br(value)}."


def build_final_result(final_state: dict) -> dict:
    sql = final_state.get("sql_used")
    data = _json_safe(final_state.get("graph") or [])
    scalar_answer = _scalar_result_answer(data)
    answer = _first_non_empty(
        final_state.get("final_response"),
        scalar_answer,
        final_state.get("text_response"),
        final_state.get("analysis_explanation"),
        "Nenhum registro encontrado para esta consulta." if sql and not data and not final_state.get("text_response") else None,
        "Consulta executada com sucesso. Veja os dados retornados abaixo." if sql and data else None,
        "Não consegui formular uma resposta.",
    )
    explanation = _clean_explanation(final_state.get("analysis_explanation"), answer)
    return {
        "answer": answer,
        "explanation": explanation,
        "sql": sql,
        "data": data,
        "valid": not bool(final_state.get("message")) and not str(answer).lower().startswith("erro"),
        "type": final_state.get("type"),
        "score": final_state.get("score"),
        "message": final_state.get("message"),
        "suggestions": final_state.get("suggestions"),
        "related_attributes": final_state.get("related_attributes"),
        "rewrite": final_state.get("rewrite"),
        "field_formats": final_state.get("field_formats") or {},
    }


# ── Persistência (roda em thread: sqlite3 é síncrono) ───────────────────────

def prepare_conversation(question: str, raw_conversation_id, contexto_id):
    """A conversa existente mantém seu contexto; uma nova precisa de um (pedido ou o único ativo)."""
    user, tenant = current()
    conversation = None
    if raw_conversation_id and not str(raw_conversation_id).startswith("local-"):
        try:
            conversation = Conversation.first(
                "id = ? AND tenant_id = ? AND user_id = ?",
                [to_db_id(raw_conversation_id), to_db_id(tenant.id), to_db_id(user.id)],
            )
        except ValueError:
            conversation = None

    with db.transaction():
        if conversation is None:
            contexto = pick_contexto(tenant, contexto_id)
            if contexto is None:
                raise ValueError("Escolha um contexto de dados para iniciar a conversa.")
            conversation = Conversation(
                user_id=user.id, tenant_id=tenant.id, contexto_id=contexto.id, title=question[:80] or "Nova conversa",
            ).insert()
        user_message = Message(conversation_id=conversation.id, role="user", content=question).insert()
    return conversation, user_message


def persist_assistant_response(conversation: Conversation, user_message: Message, question: str, result: dict) -> dict:
    answer = result.get("answer") or "Não consegui formular uma resposta."
    sql = result.get("sql")
    data = _json_safe(result.get("data") or [])
    response_type = result.get("type") or ("analysis" if sql or data else "chat")
    valid = bool(result.get("valid"))

    # Histórico guarda só o SQL; as linhas são reexecutadas ao abrir a conversa (chat.message_rows).
    metadata = {
        "sql": sql,
        "type": response_type,
        "score": 1.0 if valid else 0.0,
        "message": result.get("message") or (answer if response_type == "fallback" else None),
        "suggestions": _json_safe(result.get("suggestions") or []),
        "related_attributes": _json_safe(result.get("related_attributes") or []),
        "explanation": result.get("explanation"),
        "error": result.get("error"),
        "rewrite": _json_safe(result.get("rewrite") or {}),
        "field_formats": _json_safe(result.get("field_formats") or {}),
    }

    with db.transaction():
        assistant_msg = Message(
            conversation_id=conversation.id, role="assistant", content=answer, metadata=metadata,
        ).insert()
        conversation.updated_at = assistant_msg.created_at
        conversation.update("updated_at")
        if sql:
            QueryExecution(
                user_id=conversation.user_id,
                tenant_id=conversation.tenant_id,
                contexto_id=conversation.contexto_id,
                message_id=assistant_msg.id,
                question_original=question,
                generated_sql=sql,
                is_valid=valid,
                error_message=metadata["error"] or (metadata["message"] if not valid else None),
            ).insert()

    return {
        "conversation_id": conversation.id,
        "user_message_id": user_message.id,
        "message_id": assistant_msg.id,
        "type": response_type,
        "text": answer,
        "sql": sql,
        "data": data,
        "score": metadata["score"],
        "message": metadata["message"],
        "explanation": metadata["explanation"],
        "suggestions": metadata["suggestions"],
        "related_attributes": metadata["related_attributes"],
        "rewrite": metadata["rewrite"],
        "field_formats": metadata["field_formats"],
    }


_STATUS = {
    "orchestrator": "Roteando pergunta...",
    "mcp_tool_node": "Consultando dados...",
    "reflection_data": "Avaliando cobertura dos dados...",
    "report_agent": "Gerando relatório analítico...",
    "conversational_agent": "Gerando resposta...",
}


@rpc("chat.stream", stream=True)
async def chat_stream(params, emit):
    """Eventos `status`, `token`, `result` e `error`, os mesmos que o SSE enviava."""
    question = params.get("question")
    if not question:
        raise ApiError(400, {"error": "Pergunta obrigatória"})
    if not llm_configured():
        raise ApiError(503, {"error": LLM_KEY_MISSING})

    user, tenant = current()
    try:
        conversation, user_message = await asyncio.to_thread(
            prepare_conversation, question, params.get("conversation_id"), params.get("contexto_id"),
        )
    except ValueError as exc:
        raise ApiError(400, {"error": str(exc)}) from None

    tenant_id, user_id = tenant.id, user.id
    thread_id = f"tenant_{tenant_id}:user_{user_id}:conv_{conversation.id}"
    log_section("Chat Stream", "chat")
    log_info("chat", f"tenant={tenant_id} thread={thread_id}")
    log_info("chat", f"pergunta={question[:120]!r}")

    from agents.orchestrator import graph as graph_module
    from agents.orchestrator import router

    try:
        await emit("status", {
            "status": "processing",
            "step": "orchestrator",
            "message": "Roteando pergunta...",
            "conversation_id": conversation.id,
            "user_message_id": user_message.id,
        })

        tools = local_tools()
        router.mcp_tools = tools
        graph_module.mcp_tools = tools

        initial_state = {
            "messages": [HumanMessage(content=question)],
            "user_input": question,
            "calls": [],
            "tenant_id": tenant_id,
            "contexto_id": str(conversation.contexto_id),
            "thread_id": thread_id,
        }
        config = {
            "configurable": {"thread_id": thread_id, "user_id": user_id},
            "metadata": {"langfuse_session_id": thread_id, "langfuse_user_id": user_id},
            "callbacks": langfuse_callbacks(),
        }
        final_state = None
        has_emitted_result = False

        async with get_graph() as orchestrator_graph:
            async for mode, chunk in orchestrator_graph.astream(
                initial_state, config=config, stream_mode=["updates", "messages"]
            ):
                if mode == "messages":
                    message_chunk, metadata = chunk
                    if metadata.get("langgraph_node") == "conversational_agent" and message_chunk.text:
                        await emit("token", {"text": message_chunk.text})
                    continue

                for node_name, update in chunk.items():
                    updates_list = update if isinstance(update, list) else [update]
                    for upd in updates_list:
                        if isinstance(upd, dict):
                            final_state = {**(final_state or {}), **upd}

                    status_message = _STATUS.get(node_name, "Processando...")
                    log_info("chat", f"nó={node_name} status={status_message}")
                    await emit("status", {"status": "processing", "step": node_name, "message": status_message})

                    if node_name in ("mcp_tool_node", "report_agent", "conversational_agent"):
                        for upd in updates_list:
                            if not isinstance(upd, dict) or has_emitted_result:
                                continue
                            res = build_final_result(upd)
                            # Emite se houver algo útil para apresentar
                            if res.get("data") or res.get("sql") or (
                                res.get("answer") and res["answer"] != "Não consegui formular uma resposta."
                            ):
                                payload = await asyncio.to_thread(
                                    persist_assistant_response, conversation, user_message, question, res,
                                )
                                await emit("result", payload)
                                has_emitted_result = True

        if not final_state:
            raise ValueError("Grafo finalizou sem estado.")

        if not has_emitted_result:
            result = build_final_result(final_state)
            payload = await asyncio.to_thread(persist_assistant_response, conversation, user_message, question, result)
            log_success(
                "chat",
                f"estado final fallback type={payload.get('type')!r} rows={len(payload.get('data') or [])} "
                f"sql={str(payload.get('sql', ''))[:80]!r} answer={payload.get('text', '')[:100]!r}",
            )
            await emit("result", payload)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Erro no processamento do stream de chat")
        err_msg = str(e) or e.__class__.__name__
        await emit("error", {"message": f"Erro interno ao processar sua pergunta: {err_msg}"})
    return None


# ── Histórico ───────────────────────────────────────────────────────────────

def _message_json(message: Message) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "metadata": message.metadata,
        "created_at": api_dt(message.created_at),
    }


@rpc("chat.conversations.list")
def conversations_list(params):
    user, tenant = current()
    if tenant is None:
        return []
    conversations = Conversation.select(
        "tenant_id = ? AND user_id = ?", [to_db_id(tenant.id), to_db_id(user.id)], order="updated_at DESC, rowid DESC",
    )
    # Uma consulta para todas as mensagens (o serializer do DRF fazia uma por conversa).
    messages: dict[str, list] = {c.id: [] for c in conversations}
    if conversations:
        for message in Message.select(
            "conversation_id IN (SELECT id FROM chat_conversation WHERE tenant_id = ? AND user_id = ?)",
            [to_db_id(tenant.id), to_db_id(user.id)], order="created_at, rowid",
        ):
            messages[message.conversation_id].append(_message_json(message))
    return [
        {
            "id": c.id,
            "title": c.title,
            "contexto": c.contexto_id,
            "created_at": api_dt(c.created_at),
            "updated_at": api_dt(c.updated_at),
            "createdAt": api_dt(c.created_at),
            "updatedAt": api_dt(c.updated_at),
            "messages": messages[c.id],
        }
        for c in conversations
    ]


def _own_conversation(conversation_id) -> Conversation:
    user, tenant = current()
    try:
        cid = to_db_id(conversation_id)
    except (ValueError, TypeError, AttributeError):
        cid = None
    conversation = Conversation.first(
        "id = ? AND tenant_id = ? AND user_id = ?", [cid, to_db_id(tenant.id), to_db_id(user.id)],
    ) if cid and tenant else None
    if conversation is None:
        raise not_found("Conversation")
    return conversation


@rpc("chat.conversations.delete")
def conversations_delete(params):
    delete_conversation(_own_conversation(params.get("id")).id)
    return None


@rpc("chat.message_rows")
def message_rows(params):
    """Reexecuta o SQL de uma resposta do histórico no dados.duckdb, com a política do contexto da conversa.

    O histórico não guarda linhas de resultado: abrir uma conversa antiga mostra os dados atuais.
    """
    user, tenant = current()
    try:
        mid = to_db_id(params.get("id"))
    except (ValueError, TypeError, AttributeError):
        mid = None
    message = Message.first(
        "id = ? AND role = 'assistant' AND conversation_id IN "
        "(SELECT id FROM chat_conversation WHERE user_id = ? AND tenant_id = ?)",
        [mid, to_db_id(user.id), to_db_id(tenant.id) if tenant else None],
    ) if mid else None
    if message is None:
        raise not_found("Message")
    sql = (message.metadata or {}).get("sql")
    if not sql:
        return {"data": []}

    conversation = Conversation.first("id = ?", [to_db_id(message.conversation_id)])
    if conversation is None:
        raise not_found("Conversation")
    rows = execute_query(sql, contexto_id=conversation.contexto_id)
    if rows and isinstance(rows[0], dict) and "error" in rows[0]:
        raise ApiError(409, {"message": "os dados mudaram desde esta pergunta; refaça a pergunta", "error": rows[0]["error"]})
    return {"data": _json_safe(rows)}
