import pgvector.django.vector
from django.db import migrations


def clear_embeddings(apps, schema_editor):
    # Vetores de 3072 dims (Gemini) não convertem para 1024 (mistral-embed); são regerados pelo bootstrap.
    apps.get_model('knowledge', 'KnowledgeItem').objects.update(embedding=None)


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0002_alter_knowledgeitem_embedding'),
    ]

    operations = [
        migrations.RunPython(clear_embeddings, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='knowledgeitem',
            name='embedding',
            field=pgvector.django.vector.VectorField(blank=True, dimensions=1024, null=True),
        ),
    ]
