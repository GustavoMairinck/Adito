# Generated manually for DART-style analytic text embeddings.

import django.db.models.deletion
import pgvector.django.vector
import uuid
from django.db import migrations, models
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        VectorExtension(),
        migrations.CreateModel(
            name='AnalyticsTextEmbedding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source_table', models.CharField(max_length=128)),
                ('embedding_text', models.TextField()),
                ('payload_json', models.JSONField(blank=True, default=dict)),
                ('value_hash', models.CharField(max_length=64)),
                ('embedding', pgvector.django.vector.VectorField(blank=True, dimensions=3072, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_text_embeddings', to='core.tenant')),
            ],
            options={
                'db_table': 'analytics_text_embedding',
                'indexes': [models.Index(fields=['tenant', 'source_table'], name='ate_tenant_table_idx')],
                'constraints': [models.UniqueConstraint(fields=('tenant', 'source_table', 'value_hash'), name='uniq_analytics_text_embedding_value')],
            },
        ),
    ]
