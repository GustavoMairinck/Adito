import json
import os
import asyncio
import time
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async
import jwt
from django.conf import settings
from core.models import User
from core.rich_logging import log_error, log_info, log_section, log_success
from agents.orchestrator.graph import get_graph, mcp_tools
from agents.orchestrator.mcp_client import get_mcp_client
from langchain_core.messages import HumanMessage
from langfuse.langchain import CallbackHandler
from .models import Conversation, Message, QueryExecution
from .views import (
    _clean_explanation,
    _first_non_empty,
    _json_safe,
    _scalar_result_answer,
)


def sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@sync_to_async
def get_user_auth_data(request):
    # 1. Tenta pegar do cookie primeiro
    token = request.COOKIES.get('access_token')

    # 2. Fallback para o header Authorization
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

    if not token:
        return None
    try:
        signing_key = settings.SIMPLE_JWT.get('SIGNING_KEY', settings.SECRET_KEY)
        payload = jwt.decode(token, signing_key, algorithms=['HS256'])
        user = User.objects.select_related('tenant').get(id=payload.get('user_id'))
        return {
            'user': user,
            'tenant_id': str(user.tenant.id) if user.tenant else None,
            'db_schema': user.tenant.db_schema_name if user.tenant else None,
        }
    except Exception as e:
        log_error("auth", f"Erro ao autenticar stream: {e}")
        print(f"[Auth] Erro: {e}")
        return None


@sync_to_async
def prepare_conversation(auth_data: dict, question: str, raw_conversation_id: str | None):
    user = auth_data["user"]
    tenant = user.tenant
    conversation = None

    if raw_conversation_id and not str(raw_conversation_id).startswith("local-"):
        try:
            conversation = Conversation.objects.get(id=raw_conversation_id, tenant=tenant, user=user)
        except Conversation.DoesNotExist:
            conversation = None

    if conversation is None:
        conversation = Conversation.objects.create(user=user, tenant=tenant, title=question[:80] or "Nova conversa")

    user_message = Message.objects.create(conversation=conversation, role="user", content=question)
    return conversation, user_message


@sync_to_async
def persist_assistant_response(conversation, user_message, question: str, result: dict):
    answer = result.get("answer") or "Não consegui formular uma resposta."
    sql = result.get("sql")
    data = _json_safe(result.get("data") or [])
    response_type = result.get("type") or ("analysis" if sql or data else "chat")
    valid = bool(result.get("valid"))

    metadata = {
        "sql": sql,
        "data": data,
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

    assistant_msg = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=answer,
        metadata=metadata,
    )
    conversation.updated_at = assistant_msg.created_at
    conversation.save(update_fields=["updated_at"])

    if sql:
        QueryExecution.objects.create(
            user=conversation.user,
            tenant=conversation.tenant,
            message=assistant_msg,
            question_original=question,
            generated_sql=sql,
            is_valid=valid,
            error_message=metadata["error"] or (metadata["message"] if not valid else None),
        )

    return {
        "conversation_id": str(conversation.id),
        "user_message_id": str(user_message.id),
        "message_id": str(assistant_msg.id),
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


@csrf_exempt
async def ask_stream(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Apenas POST permitido'}, status=405)

    auth_data = await get_user_auth_data(request)
    if not auth_data:
        return JsonResponse({'error': 'Não autorizado'}, status=401)

    try:
        body = json.loads(request.body)
        question = body.get('question')
        raw_conversation_id = body.get('conversation_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not question:
        return JsonResponse({'error': 'Pergunta obrigatória'}, status=400)

    tenant_id = auth_data['tenant_id']
    db_schema  = auth_data['db_schema']
    user_id    = str(auth_data['user'].id)
    conversation, user_message = await prepare_conversation(auth_data, question, raw_conversation_id)
    thread_id = f"tenant_{tenant_id}:user_{user_id}:conv_{conversation.id}"
    log_section("Chat Stream", "chat")
    log_info("chat", f"tenant={tenant_id} thread={thread_id}")
    log_info("chat", f"pergunta={question[:120]!r}")

    async def event_generator():
        from agents.orchestrator import router, graph as graph_module
        try:
            yield sse_event("status", {
                "status": "processing",
                "step": "orchestrator",
                "message": "Roteando pergunta...",
                "conversation_id": str(conversation.id),
                "user_message_id": str(user_message.id),
            })

            async with get_mcp_client() as mcp_client:
                try:
                    tools = await asyncio.wait_for(mcp_client.get_tools(), timeout=30)
                except asyncio.TimeoutError:
                    print("[Chat Stream] Timeout ao obter ferramentas MCP (>30s)")
                    tools = []
                except Exception as e:
                    print(f"[Chat Stream] Erro ao obter ferramentas MCP: {e}")
                    tools = []
                
                router.mcp_tools = tools
                graph_module.mcp_tools = tools

                initial_state = {
                    "messages": [HumanMessage(content=question)],
                    "user_input": question,
                    "calls": [],
                    "tenant_id": tenant_id,
                    "db_schema_name": db_schema,
                    "thread_id": thread_id,
                }
                langfuse_handler = CallbackHandler()
                config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "user_id": user_id
                    },
                    "metadata": {
                        "langfuse_session_id": thread_id,
                        "langfuse_user_id": user_id
                    },
                    "callbacks": [langfuse_handler]
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
                                yield sse_event("token", {"text": message_chunk.text})
                            continue

                        for node_name, update in chunk.items():
                            updates_list = update if isinstance(update, list) else [update]
                            for upd in updates_list:
                                if isinstance(upd, dict):
                                    final_state = {**(final_state or {}), **upd}

                            status_message = {
                                "orchestrator":        "Roteando pergunta...",
                                "mcp_tool_node":       "Consultando dados...",
                                "reflection_data":     "Avaliando cobertura dos dados...",
                                "report_agent":        "Gerando relatório analítico...",
                                "conversational_agent": "Gerando resposta...",
                            }.get(node_name, "Processando...")
                            log_info("chat", f"nó={node_name} status={status_message}")
                            yield sse_event("status", {
                                "status": "processing",
                                "step": node_name,
                                "message": status_message,
                            })

                            if node_name in ("mcp_tool_node", "report_agent", "conversational_agent"):
                                for upd in updates_list:
                                    if isinstance(upd, dict):
                                        if has_emitted_result:
                                            continue
                                        res = build_final_result(upd)
                                        # Emite se houver algo útil para apresentar
                                        if res.get("data") or res.get("sql") or (res.get("answer") and res["answer"] != "Não consegui formular uma resposta."):
                                            payload = await persist_assistant_response(conversation, user_message, question, res)
                                            yield sse_event("result", payload)
                                            has_emitted_result = True

            if not final_state:
                raise ValueError("Grafo finalizou sem estado.")

            if not has_emitted_result:
                result = build_final_result(final_state)
                payload = await persist_assistant_response(conversation, user_message, question, result)
                log_success(
                    "chat",
                    (
                        "estado final fallback "
                        f"type={payload.get('type')!r} "
                        f"rows={len(payload.get('data') or [])} "
                        f"field_formats={payload.get('field_formats') or {}} "
                        f"sql={str(payload.get('sql', ''))[:80]!r} "
                        f"answer={payload.get('text', '')[:100]!r}"
                    ),
                )
                yield sse_event("result", payload)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Erro no processamento do stream de chat")
            yield sse_event("error", {"message": "Erro interno ao processar sua pergunta. Tente novamente em instantes."})

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
