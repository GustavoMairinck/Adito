# Generated manually during frontend/backend contract sync.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='widget',
            name='chart_type',
            field=models.CharField(
                choices=[
                    ('bar', 'Bar'),
                    ('line', 'Line'),
                    ('metric_card', 'Metric Card'),
                    ('horizontal_bar', 'Horizontal Bar'),
                    ('area', 'Area'),
                    ('pie', 'Pie'),
                    ('table', 'Table'),
                ],
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name='widget',
            name='mode',
            field=models.CharField(
                choices=[
                    ('static', 'Static'),
                    ('dynamic', 'Dynamic'),
                    ('auto', 'Auto'),
                ],
                default='static',
                max_length=50,
            ),
        ),
    ]
