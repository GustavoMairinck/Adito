"""Métodos básicos: saúde, usuário local, configuração multi-provedor do LLM e contextos."""
import logging
import os

import httpx

from agents.providers import (
    get_provider_spec,
    is_loopback_url,
    list_provider_specs,
    normalize_base_url,
    resolve_active_llm_config,
    validate_base_url,
)
from core.contexts import active_contextos, sync_default_contexts

from .errors import (
    ApiError,
    capacidade_plano_message,
    chave_invalida_message,
    cota_esgotada_message,
    rede_message,
)
from .registry import rpc
from .session import current

logger = logging.getLogger(__name__)

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def key_invalid_chars_message(label: str = "API") -> str:
    return (
        f"A chave tem acento, espaço ou outro caractere que não pode existir numa chave de {label}. "
        "Copie de novo direto do provedor, sem alterar."
    )


KEY_INVALID_CHARS = key_invalid_chars_message("API")
LLM_KEY_MISSING = "Configure a chave do provedor de IA em Configurações para usar o chat."


def llm_missing_message(acao: str = "usar o chat") -> str:
    cfg = resolve_active_llm_config()
    if cfg.is_local:
        return f"Configure o servidor local ({cfg.label}) e o modelo em Configurações para {acao}."
    return f"Configure a chave do {cfg.label} em Configurações para {acao}."


def llm_configured() -> bool:
    """A configuração chega do cofre do SO / llm_config.json via ambiente quando o Tauri sobe o núcleo."""
    return resolve_active_llm_config().configured


@rpc("health")
def health(params):
    return {"status": "ok"}


@rpc("me")
def me(params):
    """Usuário local do desktop, no mesmo formato que o front recebia do login + metadados do LLM ativo."""
    user, tenant = current()
    cfg = resolve_active_llm_config()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}".strip() or "Usuário local",
        "role": "admin" if user.is_staff else "user",
        "avatar": "",
        "tenant": tenant.name if tenant else None,
        "llm_configured": cfg.configured,
        "llm_provider": cfg.provider,
        "llm_provider_label": cfg.label,
        "llm_model": cfg.model,
        "llm_is_local": cfg.is_local,
    }


@rpc("config.llm_providers")
def llm_providers(params):
    """Catálogo declarativo de provedores suportados pelo Adito."""
    return list_provider_specs()


def _extract_provider_error(resp: httpx.Response, key: str = "") -> str:
    detail = ""
    try:
        payload = resp.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict) and err.get("message"):
            detail = str(err["message"]).strip()
        elif isinstance(err, str):
            detail = err.strip()
        elif payload.get("message"):
            detail = str(payload["message"]).strip()
        elif payload.get("detail"):
            detail = str(payload["detail"]).strip()
    detail = detail[:240]
    if detail and key and key in detail:
        return ""
    return detail


def _status_reason(
    status_code: int,
    label: str,
    model: str,
    base_url: str,
    is_local: bool,
    detail: str = "",
    *,
    is_gemini: bool = False,
) -> str:
    if status_code == 401:
        return f"Chave inválida para {label}."
    if status_code == 403:
        return chave_invalida_message(label)
    if status_code == 404:
        if is_gemini:
            return f"Modelo {label} ('{model}') indisponível. Verifique o modelo configurado (GEMINI_MODEL)."
        if is_local:
            return (
                f"Modelo '{model}' não encontrado no servidor local ({base_url}). "
                f"Verifique se o modelo foi baixado (ex.: ollama pull {model})."
            )
        return f"Modelo '{model}' ou endpoint não encontrado em {label}."
    if status_code == 429:
        lower = detail.lower()
        if "capacity" in lower or "service tier" in lower:
            base = capacidade_plano_message(label, model)
            return f"{base} ({detail})" if detail else base
        if detail:
            return f"Limite de uso ou plano em {label} (HTTP 429): {detail}"
        return cota_esgotada_message(label)
    if status_code == 400:
        if detail:
            return f"Solicitação recusada por {label}: {detail}"
        return f"Chave inválida ou solicitação recusada por {label}. Verifique a chave e o modelo '{model}'."
    return f"{label} respondeu com erro {status_code}." + (f" ({detail})" if detail else "")


def _test_gemini(key: str, model: str, label: str) -> dict:
    try:
        resp = httpx.get(f"{GEMINI_MODELS_URL}/{model}", headers={"x-goog-api-key": key}, timeout=15)
    except UnicodeError:
        return {"ok": False, "reason": key_invalid_chars_message(label)}
    except httpx.HTTPError:
        return {"ok": False, "reason": rede_message(label, GEMINI_MODELS_URL, False)}
    if resp.status_code == 200:
        return {"ok": True}
    detail = _extract_provider_error(resp, key)
    if detail:
        logger.warning("Validação %s (modelo=%s) retornou HTTP %s: %s", label, model, resp.status_code, detail)
    return {
        "ok": False,
        "reason": _status_reason(resp.status_code, label, model, GEMINI_MODELS_URL, False, detail, is_gemini=True),
    }


def _test_openai_compatible(key: str, model: str, base_url: str, label: str, is_local: bool) -> dict:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    endpoint = f"{base_url}/chat/completions"
    body: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": "ok"}],
        "max_tokens": 1,
    }
    try:
        resp = httpx.post(endpoint, headers=headers, json=body, timeout=15)
        if resp.status_code == 400 and "max_completion_tokens" in _extract_provider_error(resp, key).lower():
            retry_body = {
                "model": model,
                "messages": [{"role": "user", "content": "ok"}],
                "max_completion_tokens": 1,
            }
            resp = httpx.post(endpoint, headers=headers, json=retry_body, timeout=15)
    except UnicodeError:
        return {"ok": False, "reason": key_invalid_chars_message(label)}
    except httpx.HTTPError:
        return {"ok": False, "reason": rede_message(label, base_url, is_local)}

    if resp.status_code == 200:
        return {"ok": True}

    detail = _extract_provider_error(resp, key)
    if detail:
        logger.warning("Validação %s (modelo=%s) retornou HTTP %s: %s", label, model, resp.status_code, detail)
    return {"ok": False, "reason": _status_reason(resp.status_code, label, model, base_url, is_local, detail)}


@rpc("config.test_llm_key")
def test_llm_key(params):
    """Testa credencial, modelo e endpoint antes de o Tauri guardar no cofre. A chave não é gravada aqui."""
    raw_provider = str(params.get("provider") or "").strip().lower()
    try:
        spec = get_provider_spec(raw_provider or "gemini", strict=bool(raw_provider))
    except ValueError as exc:
        raise ApiError(400, {"ok": False, "reason": str(exc)}) from None

    key = str(params.get("key") or "").strip()
    raw_base_url = normalize_base_url(params.get("base_url"))
    if raw_base_url and not spec.allow_custom_base_url and raw_base_url != normalize_base_url(spec.base_url):
        return {"ok": False, "reason": f"O provedor {spec.label} não permite alterar a Base URL."}
    base_url = raw_base_url or spec.base_url

    if spec.protocol == "openai_compatible":
        url_ok, url_err = validate_base_url(base_url)
        if not url_ok:
            return {"ok": False, "reason": url_err}

    is_local = spec.protocol == "openai_compatible" and is_loopback_url(base_url)

    if not key and not is_local:
        raise ApiError(400, {"ok": False, "reason": "Informe a chave."})

    # Cabeçalho HTTP só aceita ASCII visível: acento, espaço ou quebra de linha na chave
    # estouravam UnicodeEncodeError no httpx.
    if key and (not key.isascii() or not key.isprintable() or any(c.isspace() for c in key)):
        return {"ok": False, "reason": key_invalid_chars_message(spec.label)}

    raw_model = str(params.get("model") or "").strip()
    if raw_model:
        model = raw_model
    elif spec.id == "gemini":
        from agents.config import GEMINI_MODEL

        model = (os.environ.get("GEMINI_MODEL") or GEMINI_MODEL).strip()
    else:
        model = spec.default_model

    if not model:
        return {"ok": False, "reason": f"Informe o nome do modelo para {spec.label}."}

    if spec.protocol == "gemini":
        return _test_gemini(key, model, spec.label)
    return _test_openai_compatible(key, model, base_url, spec.label, is_local)


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
