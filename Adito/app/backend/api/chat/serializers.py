from rest_framework import serializers
from .models import Conversation, Message, QueryExecution

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'metadata', 'created_at']

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'contexto', 'created_at', 'updated_at', 'createdAt', 'updatedAt', 'messages']
        read_only_fields = ['contexto']

class QueryExecutionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = QueryExecution
        fields = '__all__'

class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    # Só vale para conversa nova; a existente mantém o contexto com que foi criada.
    contexto_id = serializers.UUIDField(required=False, allow_null=True)
    execute = serializers.BooleanField(default=False)
