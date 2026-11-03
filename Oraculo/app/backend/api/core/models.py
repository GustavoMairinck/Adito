import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Contexto(models.Model):
    """Pacote de views do dados.db que um chat ou widget pode consultar.

    `views` segue o views.json: [{"name", "description", "sensitive_columns",
    "embed_columns", "local_search_columns"}]. Só as views listadas ficam expostas ao agente.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='contextos')
    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    views = models.JSONField(default=list)
    rules = models.TextField(blank=True, help_text="Regras de negócio e métricas (rules.md)")
    llm_row_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Linhas copiadas para o prompt do LLM; vazio usa o padrão")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'slug'], name='uniq_contexto_tenant_slug'),
        ]

    def __str__(self):
        return self.name

    def view_names(self) -> list[str]:
        return [view["name"].lower() for view in self.views]

    def view_config(self, name: str) -> dict | None:
        return next((view for view in self.views if view["name"].lower() == name.lower()), None)

    def sensitive_columns(self) -> set[tuple[str, str]]:
        return {
            (view["name"].lower(), column.lower())
            for view in self.views
            for column in view.get("sensitive_columns", [])
        }

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username
