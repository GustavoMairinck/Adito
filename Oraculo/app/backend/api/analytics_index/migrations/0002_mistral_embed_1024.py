import pgvector.django.vector
from django.db import migrations


def delete_embeddings(apps, schema_editor):
    # O sync pula valores pelo value_hash, então as linhas antigas (3072 dims) precisam sair para serem regeradas.
    apps.get_model('analytics_index', 'AnalyticsTextEmbedding').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('analytics_index', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_embeddings, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='analyticstextembedding',
            name='embedding',
            field=pgvector.django.vector.VectorField(blank=True, dimensions=1024, null=True),
        ),
    ]
