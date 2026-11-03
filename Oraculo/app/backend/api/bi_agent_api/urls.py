from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.serializers import EmailTokenObtainPairSerializer

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

from .views import health_check
from dashboard import views as dashboard_views
from chat.views import ask_question
from core.auth_views import cookie_login, cookie_logout
from core.views import contextos

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check),
    path('api/auth/login/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/login', EmailTokenObtainPairView.as_view()),
    path('api/auth/cookie/login', cookie_login, name='cookie_login'),
    path('api/auth/cookie/logout', cookie_logout, name='cookie_logout'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
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
    path('api/admin/data-validation', dashboard_views.data_validation),
    path('api/admin/data-validation/analytics', dashboard_views.data_validation_analytics),
    path('api/admin/system-status', dashboard_views.system_status),
    path('api/admin/data/bootstrap', dashboard_views.data_bootstrap),
]
