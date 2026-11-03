# Generated manually during frontend/backend contract sync.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_alter_widget_chart_type_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='widget',
            name='size',
            field=models.CharField(default='medium', max_length=50),
        ),
    ]
