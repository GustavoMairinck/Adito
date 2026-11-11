from django.contrib import admin
from .models import Conversation, Message, QueryExecution


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('id', 'role', 'content', 'metadata', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'title', 'created_at')
    list_filter = ('tenant',)
    search_fields = ('title', 'user__username')
    ordering = ('-created_at',)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('content',)
    ordering = ('-created_at',)


@admin.register(QueryExecution)
class QueryExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'is_valid', 'created_at')
    list_filter = ('is_valid', 'tenant')
    search_fields = ('generated_sql', 'question_original')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
