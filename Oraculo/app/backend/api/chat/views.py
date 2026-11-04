import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from asgiref.sync import async_to_sync
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Conversation, Message, QueryExecution
from .serializers import ConversationSerializer, MessageSerializer, QueryExecutionSerializer, AskRequestSerializer
from agents.bi_agent.tool import get_bi_agent, local_tools
from core.contexts import pick_contexto
from core.views import LLM_KEY_MISSING, llm_configured
from agents.orchestrator import router as orchestrator_router
from agents.orchestrator import graph as orchestrator_graph_module
from agents.orchestrator.graph import get_graph
from langchain_core.messages import HumanMessage

def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, uuid.UUID)):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
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


def _conversation_for(user, tenant, conv_id, contexto_id, title):
    """Conversa existente (mantém o contexto) ou nova com contexto obrigatório."""
    if conv_id:
        return get_object_or_404(Conversation, id=conv_id, tenant=tenant, user=user)
    contexto = pick_contexto(tenant, contexto_id)
    if contexto is None:
        raise serializers.ValidationError({"message": "Escolha um contexto de dados para iniciar a conversa."})
    return Conversation.objects.create(user=user, tenant=tenant, contexto=contexto, title=title)


async def _run_orchestrator(question: str, tenant, conversation, user) -> dict:
    tools = local_tools()
    orchestrator_router.mcp_tools = tools
    orchestrator_graph_module.mcp_tools = tools

    thread_id = f"tenant_{tenant.id}:user_{user.id}:conv_{conversation.id}"
    async with get_graph() as graph:
        final_state = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=question)],
                "user_input": question,
                "calls": [],
                "tenant_id": str(tenant.id),
                "contexto_id": str(conversation.contexto_id),
                "thread_id": thread_id,
            },
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "user_id": str(user.id),
                },
                "metadata": {
                    "langfuse_session_id": thread_id,
                    "langfuse_user_id": str(user.id),
                },
            },
        )
    return final_state or {}

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtra pelo tenant do usuário logado
        if self.request.user.is_authenticated and self.request.user.tenant:
            return self.queryset.filter(tenant=self.request.user.tenant, user=self.request.user).order_by('-updated_at')
        return self.queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        tenant = getattr(user, 'tenant', None)
        if not tenant:
            raise serializers.ValidationError({"message": "Usuário não possui tenant configurado."})
        contexto = pick_contexto(tenant, self.request.data.get('contexto_id'))
        if contexto is None:
            raise serializers.ValidationError({"message": "Escolha um contexto de dados para a conversa."})
        serializer.save(user=user, tenant=tenant, contexto=contexto)

    @action(detail=False, methods=['post'])
    def ask(self, request):
        """Endpoint para enviar perguntas ao BI Agent."""
        serializer = AskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        tenant = user.tenant
        if not tenant:
            return Response({"error": "Usuário não possui Tenant configurado."}, status=status.HTTP_400_BAD_REQUEST)

        question = serializer.validated_data['question']
        execute = serializer.validated_data['execute']
        
        # Recupera ou cria conversa
        conversation = _conversation_for(
            user, tenant,
            serializer.validated_data.get('conversation_id'),
            serializer.validated_data.get('contexto_id'),
            question[:50],
        )

        # Salva a mensagem do usuário
        Message.objects.create(conversation=conversation, role='user', content=question)

        agent = get_bi_agent()
        
        # Processa a resposta
        # Usamos o ID da conversa como thread_id pro checkpointer (se houver)
        result = agent.ask(
            question=question,
            tenant_id=str(tenant.id),
            contexto_id=str(conversation.contexto_id),
            thread_id=f"tenant_{tenant.id}:user_{user.id}:conv_{conversation.id}",
            execute=execute
        )

        # Salva a resposta do assistente
        assistant_msg = Message.objects.create(
            conversation=conversation, 
            role='assistant', 
            content=result['explanation'],
            metadata={
                "sql": result.get('sql'),
                "rewrite": _json_safe(result.get("rewrite") or {}),
                "field_formats": _json_safe(result.get("field_formats") or {}),
            }
        )

        # Registra a execução da query se houver SQL
        if result.get('sql'):
            QueryExecution.objects.create(
                user=user,
                tenant=tenant,
                contexto=conversation.contexto,
                message=assistant_msg,
                question_original=question,
                generated_sql=result['sql'],
                is_valid=result['valid'],
                error_message=result.get('error') if not result.get('valid') else None,
            )

        return Response({
            "conversation_id": str(conversation.id),
            "answer": result['explanation'],
            "sql": result['sql'],
            "data": result.get('data'),
            "field_formats": result.get("field_formats") or {},
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_question(request):
    """Contrato JSON do chat usado pelo frontend Vue.

    O backend persiste conversa, mensagens e metadados; o frontend renderiza o
    estado retornado sem manter localStorage como fonte de verdade.
    """
    serializer = AskRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user
    tenant = getattr(user, 'tenant', None)
    if not tenant:
        return Response({"message": "Usuário não possui tenant configurado."}, status=status.HTTP_400_BAD_REQUEST)
    if not llm_configured():
        return Response({"message": LLM_KEY_MISSING}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    question = serializer.validated_data['question']
    conversation = _conversation_for(
        user, tenant,
        serializer.validated_data.get('conversation_id'),
        serializer.validated_data.get('contexto_id'),
        question[:80] or 'Nova conversa',
    )

    user_msg = Message.objects.create(conversation=conversation, role='user', content=question)

    try:
        final_state = async_to_sync(_run_orchestrator)(question, tenant, conversation, user)
        sql = final_state.get("sql_used")
        data = _json_safe(final_state.get("graph") or [])
        scalar_answer = _scalar_result_answer(data)
        answer = _first_non_empty(
            final_state.get("final_response"),
            scalar_answer,
            final_state.get("text_response"),
            final_state.get("analysis_explanation"),
            "Nenhum registro encontrado para esta consulta." if sql and not data else None,
            "Consulta executada com sucesso. Veja os dados retornados abaixo." if sql and data else None,
            "Não consegui formular uma resposta.",
        )
        explanation = _clean_explanation(final_state.get("analysis_explanation"), answer)
        result = {
            "explanation": answer,
            "query_explanation": explanation,
            "sql": sql,
            "data": data,
            "valid": not bool(final_state.get("message")) and not str(answer).lower().startswith("erro"),
            "response_type": final_state.get("type"),
            "score": final_state.get("score"),
            "message": final_state.get("message"),
            "suggestions": final_state.get("suggestions"),
            "related_attributes": final_state.get("related_attributes"),
            "rewrite": final_state.get("rewrite"),
            "field_formats": final_state.get("field_formats") or {},
        }
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Erro no endpoint ask_question")
        result = {
            "explanation": "Não consegui processar sua pergunta agora. Verifique a configuração do agente e tente novamente.",
            "sql": None,
            "data": [],
            "valid": False,
            "error": str(exc),
        }

    answer = result.get('explanation') or 'Não consegui formular uma resposta.'
    sql = result.get('sql')
    data = _json_safe(result.get('data') or [])
    valid = bool(result.get('valid'))
    response_type = result.get('response_type') or ('analysis' if sql or data else 'chat')
    # Histórico guarda só o SQL; as linhas são reexecutadas ao abrir a conversa (message_rows).
    metadata = {
        "sql": sql,
        "type": response_type,
        "score": 1.0 if valid else 0.0,
        "message": result.get("message") or (answer if response_type == 'fallback' else None),
        "suggestions": _json_safe(result.get("suggestions") or []),
        "related_attributes": _json_safe(result.get("related_attributes") or []),
        "explanation": result.get("query_explanation"),
        "error": result.get("error"),
        "rewrite": _json_safe(result.get("rewrite") or {}),
        "field_formats": _json_safe(result.get("field_formats") or {}),
    }

    assistant_msg = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=answer,
        metadata=metadata,
    )
    conversation.updated_at = assistant_msg.created_at
    conversation.save(update_fields=['updated_at'])

    if sql:
        QueryExecution.objects.create(
            user=user,
            tenant=tenant,
            contexto=conversation.contexto,
            message=assistant_msg,
            question_original=question,
            generated_sql=sql,
            is_valid=valid,
            error_message=metadata["error"] or (metadata["message"] if not valid else None),
        )

    return Response({
        "conversation_id": str(conversation.id),
        "user_message_id": str(user_msg.id),
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
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def query_executions_list(request):
    """Lista as QueryExecution do tenant do usuário para auditoria de SQL gerado pela IA.

    Parâmetros opcionais:
        ?is_valid=true|false  — filtra por validez do SQL
        ?limit=N              — número máximo de registros (padrão 50, máx 200)
    """
    tenant = getattr(request.user, 'tenant', None)
    if not tenant:
        return Response({"message": "Usuário sem tenant."}, status=status.HTTP_400_BAD_REQUEST)

    qs = QueryExecution.objects.filter(tenant=tenant).select_related('user').order_by('-created_at')

    is_valid_param = request.query_params.get('is_valid')
    if is_valid_param is not None:
        qs = qs.filter(is_valid=is_valid_param.lower() == 'true')

    limit = min(int(request.query_params.get('limit', 50)), 200)
    qs = qs[:limit]

    serializer = QueryExecutionSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_rows(request, pk):
    """Reexecuta o SQL de uma resposta do histórico no dados.db, com a política do contexto da conversa.

    O histórico não guarda linhas de resultado: abrir uma conversa antiga mostra os dados atuais.
    """
    message = get_object_or_404(
        Message,
        id=pk,
        role='assistant',
        conversation__user=request.user,
        conversation__tenant=request.user.tenant,
    )
    sql = (message.metadata or {}).get('sql')
    if not sql:
        return Response({"data": []})

    rows = get_bi_agent().execute_query(sql, contexto_id=message.conversation.contexto_id)
    if rows and isinstance(rows[0], dict) and 'error' in rows[0]:
        return Response(
            {"message": "os dados mudaram desde esta pergunta; refaça a pergunta", "error": rows[0]['error']},
            status=status.HTTP_409_CONFLICT,
        )
    return Response({"data": _json_safe(rows)})
