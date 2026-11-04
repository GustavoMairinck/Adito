from django.contrib import admin
from django.urls import path, include

from .views import health_check
from dashboard import views as dashboard_views
from chat.views import ask_question
from core.views import contextos, me, test_llm_key

# Desktop sem login: não há rotas de autenticação; toda chamada leva o token local do Tauri.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check),
    path('api/me', me),
    path('api/config/test-llm-key', test_llm_key),
    path('api/contextos', contextos),
    path('api/chat', ask_question),
    path('api/chat/', include('chat.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/knowledge/', include('knowledge.urls')),
    path('api/admin/', include('knowledge.urls')),
    path('api/kpis', dashboard_views.kpis),
    path('api/projects/top', dashboard_views.top_projects),
    path('api/projects', dashboard_views.projects),
    path('api/charts', dashboard_views.charts),
    path('api/admin/system-status', dashboard_views.system_status),
    path('api/admin/data/bootstrap', dashboard_views.data_bootstrap),
]
