from rest_framework import serializers

from .models import KnowledgeItem


class KnowledgeTrainingSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeItem
        fields = [
            "id",
            "type",
            "name",
            "question",
            "content",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "metadata", "created_at", "updated_at"]

    def get_type(self, obj: KnowledgeItem) -> str:
        if obj.item_type == "query_example":
            return "sql"
        if obj.item_type == "doc":
            return "documentation"
        return obj.item_type

    def get_name(self, obj: KnowledgeItem) -> str:
        return (
            obj.metadata.get("name")
            or obj.metadata.get("question")
            or obj.metadata.get("source")
            or obj.content[:60]
        )

    def get_question(self, obj: KnowledgeItem) -> str:
        return obj.metadata.get("question", "")

    def get_content(self, obj: KnowledgeItem) -> str:
        if obj.item_type == "query_example":
            return obj.metadata.get("sql") or obj.content.removeprefix("Q: ").split("\nSQL: ", 1)[-1]
        return obj.content


class KnowledgeTrainingWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["ddl", "sql", "documentation"])
    question = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    content = serializers.CharField(trim_whitespace=True)

    def validate(self, attrs):
        if attrs["type"] == "sql" and not attrs.get("question"):
            raise serializers.ValidationError({"question": "Pergunta é obrigatória para training SQL."})
        return attrs
