from django.contrib import admin
from .models import Dashboard, Widget


class WidgetInline(admin.TabularInline):
    model = Widget
    extra = 0
    fields = ('title', 'chart_type', 'mode', 'size', 'sort_order', 'status')


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'tenant', 'created_at')
    list_filter = ('tenant',)
    search_fields = ('name', 'user__username')
    ordering = ('-created_at',)
    inlines = [WidgetInline]


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'dashboard', 'chart_type', 'mode', 'status', 'last_executed_at')
    list_filter = ('chart_type', 'mode', 'status')
    search_fields = ('title', 'question_original')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_executed_at')
