"""
Desktop sem login: um usuário local fixo e um token efêmero.

O Tauri gera um token aleatório a cada execução, passa ao backend em ORACULO_LOCAL_TOKEN
e entrega o mesmo valor ao front, que o envia no header X-Oraculo-Token. Assim outro
processo da máquina não consegue chamar a API, mesmo ela ouvindo só em 127.0.0.1.
"""
import hmac
import os

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

TOKEN_HEADER = "X-Oraculo-Token"
LOCAL_USERNAME = "local"


def get_local_user():
    """Usuário único do desktop; é staff porque administra os próprios dados."""
    from .models import Tenant, User

    tenant, _ = Tenant.objects.get_or_create(name=os.environ.get("DEFAULT_TENANT_NAME", "padrao"))
    user, created = User.objects.get_or_create(
        username=LOCAL_USERNAME,
        defaults={"tenant": tenant, "is_staff": True},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    elif user.tenant_id is None:
        user.tenant = tenant
        user.save(update_fields=["tenant"])
    return user


def token_from_headers(headers) -> str | None:
    token = headers.get(TOKEN_HEADER)
    if token:
        return token
    auth = headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None


def is_valid_token(token: str | None) -> bool:
    expected = os.environ.get("ORACULO_LOCAL_TOKEN")
    # Sem token configurado o backend não atende ninguém.
    return bool(expected and token and hmac.compare_digest(token, expected))


class LocalTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = token_from_headers(request.headers)
        if token is None:
            return None
        if not is_valid_token(token):
            raise AuthenticationFailed("Token local inválido.")
        return get_local_user(), token

    def authenticate_header(self, request):
        return TOKEN_HEADER
