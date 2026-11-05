import os

from langchain_mistralai import MistralAIEmbeddings
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import KnowledgeItem
from .serializers import KnowledgeTrainingSerializer, KnowledgeTrainingWriteSerializer


TYPE_TO_ITEM_TYPE = {
    "ddl": "ddl",
    "sql": "query_example",
    "documentation": "doc",
}


def _get_embedder() -> MistralAIEmbeddings:
    return MistralAIEmbeddings(
        model=os.environ.get("MISTRAL_EMBEDDING_MODEL", "mistral-embed"),
        api_key=os.environ.get("MISTRAL_API_KEY"),
    )


def _embedding_text(item_type: str, question: str, content: str) -> str:
    if item_type == "query_example":
        return question
    return content


def _content_for_item(item_type: str, question: str, content: str) -> str:
    if item_type == "query_example":
        return f"Q: {question}\nSQL: {content}"
    return content


class KnowledgeTrainingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = KnowledgeTrainingSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return KnowledgeItem.objects.none()
        queryset = KnowledgeItem.objects.filter(tenant=tenant).order_by("-created_at")
        item_type = self.request.query_params.get("type")
        if item_type and item_type != "all":
            queryset = queryset.filter(item_type=TYPE_TO_ITEM_TYPE.get(item_type, item_type))
        return queryset

    def _save_item(self, request, instance: KnowledgeItem | None = None) -> Response:
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return Response({"message": "Usuário sem tenant."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = KnowledgeTrainingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        public_type = serializer.validated_data["type"]
        item_type = TYPE_TO_ITEM_TYPE[public_type]
        question = serializer.validated_data.get("question", "").strip()
        raw_content = serializer.validated_data["content"].strip()
        content = _content_for_item(item_type, question, raw_content)
        metadata = {
            "name": question[:60] if item_type == "query_example" else raw_content[:60],
            "source": "admin_panel",
        }
        if item_type == "query_example":
            metadata.update({"question": question, "sql": raw_content})

        try:
            embedding = _get_embedder().embed_query(_embedding_text(item_type, question, raw_content))
        except Exception as exc:
            return Response(
                {"message": f"Não foi possível gerar embedding do training: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if instance is None:
            instance = KnowledgeItem(tenant=tenant)

        instance.item_type = item_type
        instance.content = content
        instance.metadata = metadata
        instance.embedding = embedding
        instance.save()
        return Response(
            KnowledgeTrainingSerializer(instance).data,
            status=status.HTTP_200_OK if request.method in ("PUT", "PATCH") else status.HTTP_201_CREATED,
        )

    def create(self, request, *args, **kwargs):
        return self._save_item(request)

    def update(self, request, *args, **kwargs):
        return self._save_item(request, self.get_object())

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
