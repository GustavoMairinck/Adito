from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KnowledgeTrainingViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"trainings", KnowledgeTrainingViewSet, basename="training")

urlpatterns = [
    path("", include(router.urls)),
]
