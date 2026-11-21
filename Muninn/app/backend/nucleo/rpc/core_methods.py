"""Métodos básicos: saúde, usuário local, chave do LLM e contextos."""
import os

import httpx

from core.contexts import active_contextos, sync_default_contexts

from .errors import ApiError
from .registry import rpc
from .session import current

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
KEY_INVALID_CHARS = (
    "A chave tem acento, espaço ou outro caractere que não pode existir numa chave do Gemini. "
    "Copie de novo direto do Google AI Studio, sem alterar."
)
LLM_KEY_MISSING = "Configure a chave do Gemini em Configurações para usar o chat."


def llm_configured() -> bool:
    """A chave chega do cofre do SO via ambiente quando o Tauri sobe o núcleo."""
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


@rpc("health")
def health(params):
    return {"status": "ok"}


@rpc("me")
def me(params):
    """Usuário local do desktop, no mesmo formato que o front recebia do login."""
    user, tenant = current()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}".strip() or "Usuário local",
        "role": "admin" if user.is_staff else "user",
        "avatar": "",
        "tenant": tenant.name if tenant else None,
        "llm_configured": llm_configured(),
    }


@rpc("config.test_llm_key")
def test_llm_key(params):
    """Testa uma chave do Gemini antes de o Tauri guardá-la no cofre. A chave não é gravada aqui."""
    key = str(params.get("key") or "").strip()
    if not key:
        raise ApiError(400, {"ok": False, "reason": "Informe a chave."})
    # Cabeçalho HTTP só aceita ASCII visível: acento, espaço ou quebra de linha na chave (colada errada)
    # estouravam UnicodeEncodeError no httpx e chegavam como um erro "'ascii' codec can't encode...".
    if not key.isascii() or not key.isprintable() or any(c.isspace() for c in key):
        return {"ok": False, "reason": KEY_INVALID_CHARS}
    try:
        from agents.config import GEMINI_MODEL

        resp = httpx.get(f"{GEMINI_MODELS_URL}/{GEMINI_MODEL}", headers={"x-goog-api-key": key}, timeout=15)
    except (httpx.HTTPError, UnicodeError):
        return {"ok": False, "reason": "Sem conexão com o Gemini. Verifique a internet e tente de novo."}
    if resp.status_code == 200:
        return {"ok": True}
    reasons = {
        400: "Chave inválida ou solicitação recusada pelo Gemini.",
        401: "Chave inválida.",
        403: "Chave sem permissão para a API ou para o modelo configurado.",
        404: "Modelo Gemini indisponível. Verifique GEMINI_MODEL no backend.",
        429: "Cota da chave esgotada ou limite de uso atingido.",
    }
    return {"ok": False, "reason": reasons.get(resp.status_code, f"O Gemini respondeu com erro {resp.status_code}.")}


@rpc("contextos.list")
def contextos(params):
    """Contextos ativos para o seletor do chat e do dashboard (sem colunas sensíveis)."""
    user, tenant = current()
    if tenant is None:
        return []
    rows = active_contextos(tenant.id)
    if not rows:
        sync_default_contexts(tenant)
        rows = active_contextos(tenant.id)
    return [
        {
            "id": contexto.id,
            "slug": contexto.slug,
            "name": contexto.name,
            "description": contexto.description,
            "views": [{"name": view["name"], "description": view.get("description", "")} for view in contexto.views],
        }
        for contexto in rows
    ]
