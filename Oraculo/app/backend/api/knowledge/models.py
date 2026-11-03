import uuid
from django.db import models
from core.models import Tenant
from core.vectors import EmbeddingField

class KnowledgeItem(models.Model):
    ITEM_TYPES = [
        ('ddl', 'DDL'),
        ('doc', 'Documentation'),
        ('query_example', 'Query Example'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='knowledge_items')
    item_type = models.CharField(max_length=50, choices=ITEM_TYPES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    embedding = EmbeddingField(dimensions=1024, null=True, blank=True) # mistral-embed dimensions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['item_type']),
        ]

    def __str__(self):
        return f"{self.get_item_type_display()} - {self.id}"
