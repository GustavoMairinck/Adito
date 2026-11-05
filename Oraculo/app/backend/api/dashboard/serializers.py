from rest_framework import serializers
from .models import Dashboard, Widget

class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = '__all__'
        read_only_fields = ['dashboard', 'last_executed_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'sql_validated': {'required': False, 'allow_blank': True},
            'mode': {'required': False},
            'cache_ttl_hours': {'required': False},
            'limit_rows': {'required': False},
            'sort_order': {'required': False},
            'size': {'required': False},
            'grid_x': {'required': False},
            'grid_y': {'required': False},
            'grid_w': {'required': False},
            'grid_h': {'required': False},
        }

class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)

    class Meta:
        model = Dashboard
        fields = ['id', 'name', 'description', 'created_at', 'widgets']
