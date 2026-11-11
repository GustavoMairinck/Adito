from django.contrib import admin
from .models import KnowledgeItem


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'item_type', 'content_preview', 'created_at')
    list_filter = ('tenant', 'item_type')
    search_fields = ('content',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    exclude = ('embedding',)

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Conteúdo'
