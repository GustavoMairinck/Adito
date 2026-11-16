from django.db import migrations


def reset_embeddings(apps, schema_editor):
    # Os vetores dos provedores pertencem a espaços diferentes.
    database = schema_editor.connection.alias
    apps.get_model('knowledge', 'KnowledgeItem').objects.using(database).update(embedding=None)
    apps.get_model('analytics_index', 'AnalyticsTextEmbedding').objects.using(database).all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('knowledge', '0001_initial'),
        ('analytics_index', '0002_initial'),
    ]
    operations = [migrations.RunPython(reset_embeddings, migrations.RunPython.noop)]
