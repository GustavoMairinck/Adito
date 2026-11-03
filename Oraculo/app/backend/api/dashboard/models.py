import uuid
from django.db import models
from core.models import User, Tenant

class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboards')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='dashboards')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Widget(models.Model):
    CHART_TYPES = [
        ('bar', 'Bar'),
        ('line', 'Line'),
        ('metric_card', 'Metric Card'),
        ('horizontal_bar', 'Horizontal Bar'),
        ('area', 'Area'),
        ('pie', 'Pie'),
        ('table', 'Table'),
    ]
    MODE_CHOICES = [
        ('static', 'Static'),
        ('dynamic', 'Dynamic'),
        ('auto', 'Auto'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    title = models.CharField(max_length=255)
    question_original = models.TextField()
    sql_validated = models.TextField()
    chart_type = models.CharField(max_length=50, choices=CHART_TYPES)
    mode = models.CharField(max_length=50, choices=MODE_CHOICES, default='static')
    cache_ttl_hours = models.IntegerField(default=4)
    size = models.CharField(max_length=50, default='medium')
    grid_x = models.IntegerField(default=0)
    grid_y = models.IntegerField(default=0)
    grid_w = models.IntegerField(default=4)
    grid_h = models.IntegerField(default=4)
    limit_rows = models.IntegerField(default=0, help_text="0 is unlimited")
    sort_order = models.CharField(max_length=50, default='none')
    status = models.CharField(max_length=50, default='OK')
    last_executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
