from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, message_rows, query_executions_list

from .stream_views import ask_stream

router = DefaultRouter(trailing_slash=False)
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('stream', ask_stream),
    path('messages/<uuid:pk>/rows', message_rows),
    path('query-executions', query_executions_list, name='query-executions-list'),
    path('', include(router.urls)),
]
