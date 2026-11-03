import uuid

from django.db import models
from core.models import Contexto, Tenant
from core.vectors import EmbeddingField


class AnalyticsTextEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='analytics_text_embeddings')
    contexto = models.ForeignKey(Contexto, on_delete=models.CASCADE, related_name='analytics_text_embeddings')
    source_table = models.CharField(max_length=128)
    embedding_text = models.TextField()
    payload_json = models.JSONField(default=dict, blank=True)
    value_hash = models.CharField(max_length=64)
    embedding = EmbeddingField(dimensions=1024, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_text_embedding'
        constraints = [
            models.UniqueConstraint(
                fields=['contexto', 'source_table', 'value_hash'],
                name='uniq_analytics_text_embedding_value',
            ),
        ]
        indexes = [
            models.Index(fields=['contexto', 'source_table'], name='ate_contexto_table_idx'),
        ]

    def __str__(self):
        return f"{self.source_table} - {self.embedding_text[:80]}"
