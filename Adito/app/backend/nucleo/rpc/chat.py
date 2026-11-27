"""Chat: pergunta com streaming, histórico de conversas e reexecução do SQL das respostas."""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from datetime import date, datetime
from decimal import Decimal

from langchain_core.messages import HumanMessage

from agents.bi_agent.agent import BIAgentCancelled, execute_query, reset_cancel_event, set_cancel_event
from agents.bi_agent.tool import local_tools, reset_trace_sink, set_trace_sink
from agents.config import langfuse_callbacks
from agents.dashboard_agent import choose_chart_with_agent, plan_chart
from agents.dashboard_agent.agent import is_chat_chart_type
from agents.orchestrator.graph import get_graph
from core import db
from core.contexts import pick_contexto
from core.db import api_dt, to_db_id
from core.records import Contexto, Conversation, Message, QueryExecution, delete_conversation
from core.rich_logging import log_info, log_section, log_success

from .core_methods import LLM_KEY_MISSING, llm_configured, llm_missing_message
from .errors import ApiError, bad_request, llm_error_message, not_found
from .params import Bool, Choice, Str, Uuid, validate
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


def persist_assistant_response(
    conversation: Conversation,
    user_message: Message,
    question: str,
    result: dict,
    cancel_event: threading.Event | None = None,
) -> dict:
    if cancel_event is not None and cancel_event.is_set():
        raise BIAgentCancelled("Resposta cancelada antes de persistir.")

    answer = result.get("answer") or "Não consegui formular uma resposta."
    sql = result.get("sql")
    data = _json_safe(result.get("data") or [])
    response_type = result.get("type") or ("analysis" if sql or data else "chat")
    valid = bool(result.get("valid"))

    # Histórico guarda só o SQL; as linhas são reexecutadas ao abrir a conversa (chat.message_rows).
    trace = _json_safe(result.get("trace")) if result.get("trace") is not None else None
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
        "trace": trace,
        # Tipo de gráfico escolhido pelo agente de painéis; reabrir a conversa mantém a escolha.
        "chart_type": result.get("chart_type") if is_chat_chart_type(result.get("chart_type")) else None,
        "chart_source": result.get("chart_source"),
    }

    with db.transaction():
        if cancel_event is not None and cancel_event.is_set():
            raise BIAgentCancelled("Resposta cancelada antes da gravação.")
        if Conversation.first("id = ?", [to_db_id(conversation.id)]) is None:
            raise BIAgentCancelled("Conversa excluída antes da gravação.")
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
        if cancel_event is not None and cancel_event.is_set():
            # Força rollback da transação se $cancel chegou durante a gravação (BR01).
            raise BIAgentCancelled("Resposta cancelada durante a gravação.")

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
        "trace": trace,
        "chart_type": metadata["chart_type"],
        "chart_source": metadata["chart_source"],
    }


async def add_chart_suggestion(result: dict, question: str, emit, cancel_event: threading.Event) -> dict:
    """Pede ao agente de painéis o tipo de gráfico. O LLM só é chamado nos casos ambíguos."""
    if result.get("type") == "fallback":
        return result
    plan = plan_chart(question, result.get("data") or [])
    suggestion = plan.suggestion()
    if plan.needs_agent:
        await emit("status", {"status": "processing", "step": "dashboard_agent", "message": "Escolhendo o gráfico..."})
        suggestion = await asyncio.to_thread(choose_chart_with_agent, question, plan)
        if cancel_event.is_set():
            raise asyncio.CancelledError()
    if suggestion.chart_type:
        log_info("chat", f"gráfico={suggestion.chart_type} fonte={suggestion.source}")
    return {**result, "chart_type": suggestion.chart_type, "chart_source": suggestion.source}


_STATUS = {
    "orchestrator": "Roteando pergunta...",
    "mcp_tool_node": "Consultando dados...",
    "conversational_agent": "Gerando resposta...",
    "guard_node": "Gerando resposta...",
}


def _short_summary(text: str | None, max_len: int = 120) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


class _TraceSession:
    """Acumula e emite em tempo real as etapas de raciocínio do chat (`step_*`)."""

    def __init__(self, emit, loop: asyncio.AbstractEventLoop):
        self._emit = emit
        self._loop = loop
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._steps: list[dict] = []
        self._by_id: dict[str, dict] = {}
        self.active_step_id: str | None = None
        self.compact: bool = False
        self.routed_to_bi: bool = False

    def _get_or_create(self, step_id: str) -> dict:
        step = self._by_id.get(step_id)
        if step is None:
            step = {
                "id": step_id,
                "title": step_id,
                "subtitle": "",
                "status": "running",
                "details": [],
            }
            self._by_id[step_id] = step
            self._steps.append(step)
        return step

    def _record(self, event: str, data: dict) -> dict | None:
        with self._lock:
            step_id = str(data.get("step_id") or data.get("id") or self.active_step_id or "routing")
            payload = {**data, "step_id": step_id}
            if event == "step_start":
                existing = self._by_id.get(step_id)
                if existing is not None and existing.get("status") == "running":
                    return None
                step = self._get_or_create(step_id)
                step["title"] = str(data.get("title") or step["title"])
                step["subtitle"] = str(data.get("subtitle") or step["subtitle"])
                if data.get("header_status"):
                    step["header_status"] = str(data["header_status"])
                step["status"] = "running"
                self.active_step_id = step_id
                return payload
            if event == "step_detail":
                detail = str(data.get("detail") or "").strip()
                if not detail:
                    return None
                step = self._get_or_create(step_id)
                if not step["details"] or step["details"][-1] != detail:
                    step["details"].append(detail)
                return {**payload, "detail": detail}
            if event == "step_code":
                code = str(data.get("code") or "").strip()
                if not code:
                    return None
                step = self._get_or_create(step_id)
                language = str(data.get("language") or "sql")
                step["code"] = code
                step["language"] = language
                return {**payload, "code": code, "language": language}
            if event == "step_complete":
                step = self._get_or_create(step_id)
                if step.get("status") in ("done", "error"):
                    return None
                step["status"] = "done"
                detail = str(data.get("detail") or "").strip()
                if detail and (not step["details"] or step["details"][-1] != detail):
                    step["details"].append(detail)
                if self.active_step_id == step_id:
                    self.active_step_id = None
                return {**payload, **({"detail": detail} if detail else {})}
            if event == "step_error":
                step = self._get_or_create(step_id)
                step["status"] = "error"
                detail = str(data.get("detail") or "").strip()
                if detail and (not step["details"] or step["details"][-1] != detail):
                    step["details"].append(detail)
                if self.active_step_id == step_id:
                    self.active_step_id = None
                return {**payload, **({"detail": detail} if detail else {})}
            return payload

    async def emit_event(self, event: str, data: dict) -> None:
        payload = self._record(event, data)
        if payload is not None:
            await self._emit(event, payload)

    def emit_sync(self, event: str, data: dict) -> None:
        """Ponte thread-safe chamada a partir da thread do bi_agent."""
        payload = self._record(event, data)
        if payload is None:
            return
        try:
            fut = asyncio.run_coroutine_threadsafe(self._emit(event, payload), self._loop)
            fut.result(timeout=5)
        except Exception as exc:
            logger.debug("Falha ao encaminhar evento de trace (%s): %s", event, exc)

    def step_status(self, step_id: str) -> str | None:
        with self._lock:
            step = self._by_id.get(step_id)
            return step.get("status") if step else None

    def has_code(self, step_id: str) -> bool:
        with self._lock:
            step = self._by_id.get(step_id)
            return bool(step and step.get("code"))

    async def start_routing(self) -> None:
        await self.emit_event("step_start", {
            "step_id": "routing",
            "title": "Orquestrador",
            "subtitle": "Interpretando a solicitação e definindo a estratégia de busca.",
            "header_status": "Analisando contexto...",
        })

    async def finish_routing(self, calls: list[dict]) -> None:
        if self.step_status("routing") == "done":
            return
        intents = [str(c.get("intent") or "") for c in calls if isinstance(c, dict)]
        is_bi = any(i not in ("", "conversational", "blocked", "out_of_scope") for i in intents)
        self.routed_to_bi = is_bi
        first_call = calls[0] if calls and isinstance(calls[0], dict) else {}
        instruction = _short_summary(first_call.get("delegation_instruction"))

        if is_bi:
            detail = (
                f"Encaminhando para consulta analítica: {instruction}"
                if instruction
                else "Encaminhando para o agente de dados na base do IFES."
            )
        elif "blocked" in intents:
            detail = "Solicitação redirecionada pela política de segurança."
        elif "out_of_scope" in intents:
            detail = "Solicitação fora do domínio de pesquisa e extensão do IFES."
        else:
            detail = (
                f"Resposta direta: {instruction}"
                if instruction
                else "Respondendo diretamente sem consulta ao banco analítico."
            )

        await self.emit_event("step_detail", {"step_id": "routing", "detail": detail})
        await self.emit_event("step_complete", {"step_id": "routing"})

        if is_bi:
            await self.emit_event("step_start", {
                "step_id": "query",
                "title": "Agente de dados",
                "subtitle": "Buscando dados na base do IFES e aplicando regras de verificação.",
                "header_status": "Consultando base...",
            })
        else:
            self.compact = True
            await self.emit_event("step_start", {
                "step_id": "synthesis",
                "title": "Adito",
                "subtitle": "Estruturando a resposta.",
                "header_status": "Estruturando resposta...",
            })

    async def finalize_before_result(self, node_name: str, res: dict) -> None:
        if node_name in ("conversational_agent", "guard_node") and not self.routed_to_bi:
            self.compact = True
        if self.step_status("routing") == "running":
            await self.emit_event("step_complete", {"step_id": "routing"})
        if self.routed_to_bi:
            sql = str(res.get("sql") or "").strip()
            if sql and not self.has_code("query"):
                await self.emit_event("step_code", {"step_id": "query", "language": "sql", "code": sql})
            if self.step_status("query") == "running":
                rows = res.get("data") or []
                is_fallback = res.get("type") == "fallback" or not res.get("valid", True)
                if is_fallback:
                    await self.emit_event("step_error", {
                        "step_id": "query",
                        "detail": "Consulta finalizada com alerta.",
                    })
                else:
                    n = len(rows)
                    detail = "Nenhum registro encontrado." if n == 0 else ("1 registro encontrado." if n == 1 else f"{n} registros encontrados.")
                    await self.emit_event("step_complete", {"step_id": "query", "detail": detail})
        if self.step_status("synthesis") is None:
            await self.emit_event("step_start", {
                "step_id": "synthesis",
                "title": "Adito",
                "subtitle": "Consolidando os resultados encontrados." if self.routed_to_bi else "Estruturando a resposta.",
                "header_status": "Estruturando resposta...",
            })
        if self.step_status("synthesis") == "running":
            await self.emit_event("step_complete", {"step_id": "synthesis", "detail": "Resposta concluída."})

    async def mark_error(self, detail: str) -> None:
        target = self.active_step_id or (self._steps[-1]["id"] if self._steps else "routing")
        await self.emit_event("step_error", {"step_id": target, "detail": detail})

    def snapshot(self) -> dict:
        with self._lock:
            steps_copy = [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "subtitle": s["subtitle"],
                    "status": s["status"],
                    "details": list(s.get("details") or []),
                    **({"code": s["code"], "language": s.get("language", "sql")} if s.get("code") else {}),
                    **({"header_status": s["header_status"]} if s.get("header_status") else {}),
                }
                for s in self._steps
            ]
            return {
                "steps": steps_copy,
                "duration_ms": max(0, int((time.monotonic() - self._started_at) * 1000)),
                "compact": self.compact,
            }


@rpc("chat.stream", stream=True)
async def chat_stream(params, emit):
    """Eventos `status`, `step_*`, `token`, `result` e `error`, os mesmos que o SSE enviava."""
    question = params.get("question")
    if not question:
        raise ApiError(400, {"error": "Pergunta obrigatória"})
    if not llm_configured():
        raise ApiError(503, {"error": llm_missing_message("usar o chat")})

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

    cancel_event = threading.Event()
    cancel_token = set_cancel_event(cancel_event)
    trace = _TraceSession(emit, asyncio.get_running_loop())
    trace_token = set_trace_sink(trace.emit_sync)

    try:
        await emit("status", {
            "status": "processing",
            "step": "orchestrator",
            "message": "Roteando pergunta...",
            "conversation_id": conversation.id,
            "user_message_id": user_message.id,
        })
        await trace.start_routing()

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
                if cancel_event.is_set():
                    raise asyncio.CancelledError()
                if mode == "messages":
                    message_chunk, metadata = chunk
                    if metadata.get("langgraph_node") == "conversational_agent" and message_chunk.text:
                        await emit("token", {"text": message_chunk.text})
                    continue

                for node_name, update in chunk.items():
                    if cancel_event.is_set():
                        raise asyncio.CancelledError()
                    updates_list = update if isinstance(update, list) else [update]
                    for upd in updates_list:
                        if isinstance(upd, dict):
                            final_state = {**(final_state or {}), **upd}

                    if node_name == "orchestrator":
                        calls = []
                        for upd in updates_list:
                            if isinstance(upd, dict) and isinstance(upd.get("calls"), list):
                                calls.extend(upd["calls"])
                        await trace.finish_routing(calls)

                    status_message = _STATUS.get(node_name, "Processando...")
                    log_info("chat", f"nó={node_name} status={status_message}")
                    await emit("status", {"status": "processing", "step": node_name, "message": status_message})

                    if node_name in ("mcp_tool_node", "conversational_agent", "guard_node"):
                        for upd in updates_list:
                            if not isinstance(upd, dict) or has_emitted_result:
                                continue
                            if cancel_event.is_set():
                                raise asyncio.CancelledError()
                            res = build_final_result(upd)
                            # Emite se houver algo útil para apresentar
                            if res.get("data") or res.get("sql") or (
                                res.get("answer") and res["answer"] != "Não consegui formular uma resposta."
                            ):
                                res = await add_chart_suggestion(res, question, emit, cancel_event)
                                await trace.finalize_before_result(node_name, res)
                                res["trace"] = trace.snapshot()
                                payload = await asyncio.to_thread(
                                    persist_assistant_response, conversation, user_message, question, res, cancel_event,
                                )
                                if cancel_event.is_set():
                                    raise asyncio.CancelledError()
                                await emit("result", payload)
                                has_emitted_result = True

        if cancel_event.is_set():
            raise asyncio.CancelledError()

        if not final_state:
            raise ValueError("Grafo finalizou sem estado.")

        if not has_emitted_result:
            result = await add_chart_suggestion(build_final_result(final_state), question, emit, cancel_event)
            await trace.finalize_before_result("fallback", result)
            result["trace"] = trace.snapshot()
            payload = await asyncio.to_thread(
                persist_assistant_response, conversation, user_message, question, result, cancel_event,
            )
            if cancel_event.is_set():
                raise asyncio.CancelledError()
            log_success(
                "chat",
                f"estado final fallback type={payload.get('type')!r} rows={len(payload.get('data') or [])} "
                f"sql={str(payload.get('sql', ''))[:80]!r} answer={payload.get('text', '')[:100]!r}",
            )
            await emit("result", payload)

    except (asyncio.CancelledError, BIAgentCancelled):
        cancel_event.set()
        log_info("chat", f"stream cancelado pelo usuário thread={thread_id}")
        raise asyncio.CancelledError()
    except Exception as e:
        logger.exception("Erro no processamento do stream de chat")
        err_msg = str(e) or e.__class__.__name__
        friendly = llm_error_message(e) or f"Erro interno ao processar sua pergunta: {err_msg}"
        await trace.mark_error(friendly)
        await emit("error", {"message": friendly})
    finally:
        reset_trace_sink(trace_token)
        reset_cancel_event(cancel_token)
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
        "tenant_id = ? AND user_id = ?",
        [to_db_id(tenant.id), to_db_id(user.id)],
        order="is_pinned DESC, updated_at DESC, rowid DESC",
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
            "is_pinned": bool(c.is_pinned),
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


CONVERSATION_UPDATE_FIELDS = {
    "title": Str(max_length=255, allow_blank=False),
    "is_pinned": Bool(),
}


@rpc("chat.conversations.update")
def conversations_update(params):
    """Atualiza título e/ou estado fixado da conversa sem alterar updated_at."""
    conversation = _own_conversation(params.get("id"))
    data = validate(
        CONVERSATION_UPDATE_FIELDS,
        {k: v for k, v in params.items() if k in CONVERSATION_UPDATE_FIELDS},
        partial=True,
    )
    if not data:
        raise bad_request({"detail": "Informe title ou is_pinned para atualizar a conversa."})
    fields_to_update: list[str] = []
    if "title" in data:
        conversation.title = data["title"]
        fields_to_update.append("title")
    if "is_pinned" in data:
        conversation.is_pinned = bool(data["is_pinned"])
        fields_to_update.append("is_pinned")
    conversation.update(*fields_to_update)
    return {
        "id": conversation.id,
        "title": conversation.title,
        "is_pinned": bool(conversation.is_pinned),
        "contexto": conversation.contexto_id,
        "created_at": api_dt(conversation.created_at),
        "updated_at": api_dt(conversation.updated_at),
        "createdAt": api_dt(conversation.created_at),
        "updatedAt": api_dt(conversation.updated_at),
    }


@rpc("chat.conversations.delete")
def conversations_delete(params):
    delete_conversation(_own_conversation(params.get("id")).id)
    return None


@rpc("chat.message_rows")
def message_rows(params):
    """Reexecuta o SQL de uma resposta do histórico no dados.db, com a política do contexto da conversa.

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
    if _query_failed(rows):
        raise ApiError(409, {"message": "os dados mudaram desde esta pergunta; refaça a pergunta", "error": rows[0]["error"]})
    return {"data": _json_safe(rows)}


def _query_failed(rows) -> bool:
    """`execute_query` sinaliza falha devolvendo exatamente `[{"error": "<mensagem>"}]`.

    Mesma regra para `chat.message_rows` e `chat.report_rows`: um resultado legítimo que tenha uma
    coluna `error` ao lado de outras, ou mais de uma linha, continua sendo dado.
    """
    return (
        isinstance(rows, list)
        and len(rows) == 1
        and isinstance(rows[0], dict)
        and set(rows[0]) == {"error"}
    )


# ── Relatórios (EPIC-14) ────────────────────────────────────────────────────
# O relatório é uma mensagem da conversa (metadata.type = "report") montada por modelo fixo, sem LLM.
# Guarda só a definição das seções; as linhas são reexecutadas a cada exibição (números atuais).

REPORT_MAX_SECTIONS = 20
REPORT_CHART_TYPES = ("bar", "horizontal_bar", "line", "area", "pie")


def _report_eligible(message: Message | None) -> bool:
    """Resposta de análise com SQL (BR01): fora conversa simples, aviso de "não encontrei" e outros relatórios."""
    if message is None or message.role != "assistant":
        return False
    metadata = message.metadata or {}
    return metadata.get("type") == "analysis" and bool(metadata.get("sql"))


@rpc("chat.reports.create")
def reports_create(params):
    """Grava o relatório como mensagem da conversa. Não chama LLM nem grava QueryExecution."""
    conversation = _own_conversation(params.get("conversation_id"))
    title = validate({"title": Str(required=True, max_length=200, allow_blank=False)}, params)["title"]
    sections_in = params.get("sections")
    if not isinstance(sections_in, list) or not sections_in:
        raise ApiError(400, {"sections": ["Escolha ao menos uma resposta para o relatório."]})
    if len(sections_in) > REPORT_MAX_SECTIONS:
        raise ApiError(400, {"sections": [f"O relatório aceita no máximo {REPORT_MAX_SECTIONS} seções."]})

    sections, seen = [], set()
    for item in sections_in:
        if not isinstance(item, dict):
            raise ApiError(400, {"sections": ["Seção inválida."]})
        section = validate({
            "message_id": Uuid(required=True),
            "title": Str(required=True, max_length=300, allow_blank=False),
            "chart_type": Choice(choices=REPORT_CHART_TYPES, default=None, allow_null=True),
        }, item)
        mid = to_db_id(section["message_id"])
        if mid in seen:
            raise ApiError(400, {"sections": ["A mesma resposta foi escolhida duas vezes."]})
        seen.add(mid)
        source = Message.first("id = ? AND conversation_id = ?", [mid, to_db_id(conversation.id)])
        if not _report_eligible(source):
            raise ApiError(400, {"sections": ["Só entram respostas com dados desta conversa."]})
        metadata = source.metadata or {}
        chart_type = section.get("chart_type") or metadata.get("chart_type")
        sections.append({
            "source_message_id": source.id,
            "title": section["title"],
            "sql": metadata["sql"],
            "field_formats": metadata.get("field_formats") or {},
            "chart_type": chart_type if chart_type in REPORT_CHART_TYPES else None,
        })

    contexto = Contexto.first("id = ?", [to_db_id(conversation.contexto_id)]) if conversation.contexto_id else None
    metadata = {
        "type": "report",
        "title": title,
        "contexto_nome": contexto.name if contexto else None,
        "sections": sections,
    }
    with db.transaction():
        message = Message(conversation_id=conversation.id, role="assistant", content=title, metadata=metadata).insert()
        conversation.updated_at = message.created_at
        conversation.update("updated_at")
    return _message_json(message)


@rpc("chat.report_rows")
def report_rows(params):
    """Reexecuta o SQL de cada seção com a política do contexto. Uma seção com erro não derruba as outras."""
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
    if message is None or (message.metadata or {}).get("type") != "report":
        raise not_found("Report")
    conversation = Conversation.first("id = ?", [to_db_id(message.conversation_id)])
    if conversation is None:
        raise not_found("Conversation")

    results = []
    for section in message.metadata.get("sections") or []:
        try:
            rows = execute_query(section.get("sql") or "", contexto_id=conversation.contexto_id)
        except Exception:  # noqa: BLE001 - uma seção quebrada não derruba o relatório
            logger.exception("Falha ao reexecutar seção do relatório %s", message.id)
            rows = [{"error": "falha ao executar"}]
        if _query_failed(rows):
            results.append({"data": [], "error": "os dados mudaram desde a pergunta"})
        else:
            results.append({"data": _json_safe(rows), "error": None})
    return {"sections": results}
