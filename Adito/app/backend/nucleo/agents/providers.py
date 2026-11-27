"""Catálogo declarativo de provedores de IA (BYOK) e resolução de configuração ativa."""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_PROVIDER_ID = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    protocol: str  # "gemini" | "openai_compatible"
    base_url: str
    default_model: str
    requires_key: bool = True
    allow_custom_base_url: bool = False

    def to_public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "requires_key": self.requires_key,
            "allow_custom_base_url": self.allow_custom_base_url,
        }


PROVIDER_CATALOG: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        id="gemini",
        label="Gemini",
        protocol="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model=DEFAULT_GEMINI_MODEL,
        requires_key=True,
        allow_custom_base_url=False,
    ),
    ProviderSpec(
        id="openai",
        label="OpenAI",
        protocol="openai_compatible",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        requires_key=True,
        allow_custom_base_url=False,
    ),
    ProviderSpec(
        id="openrouter",
        label="OpenRouter",
        protocol="openai_compatible",
        base_url="https://openrouter.ai/api/v1",
        default_model="google/gemini-2.5-flash",
        requires_key=True,
        allow_custom_base_url=False,
    ),
    ProviderSpec(
        id="mistral",
        label="Mistral AI",
        protocol="openai_compatible",
        base_url="https://api.mistral.ai/v1",
        default_model="ministral-8b-latest",
        requires_key=True,
        allow_custom_base_url=False,
    ),
    ProviderSpec(
        id="zai",
        label="Z.AI (GLM)",
        protocol="openai_compatible",
        base_url="https://api.z.ai/api/paas/v4",
        default_model="glm-4.5-flash",
        requires_key=True,
        allow_custom_base_url=True,
    ),
    ProviderSpec(
        id="together",
        label="Together AI",
        protocol="openai_compatible",
        base_url="https://api.together.xyz/v1",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        requires_key=True,
        allow_custom_base_url=False,
    ),
    ProviderSpec(
        id="fireworks",
        label="Fireworks AI",
        protocol="openai_compatible",
        base_url="https://api.fireworks.ai/inference/v1",
        default_model="accounts/fireworks/models/llama-v3p3-70b-instruct",
        requires_key=True,
        allow_custom_base_url=False,
    ),
    ProviderSpec(
        id="ollama",
        label="Ollama (Local)",
        protocol="openai_compatible",
        base_url="http://localhost:11434/v1",
        default_model="qwen2.5:7b",
        requires_key=False,
        allow_custom_base_url=True,
    ),
)

PROVIDERS_BY_ID: dict[str, ProviderSpec] = {spec.id: spec for spec in PROVIDER_CATALOG}


@dataclass(frozen=True)
class ActiveLLMConfig:
    provider: str
    label: str
    protocol: str
    model: str
    base_url: str
    api_key: str | None
    is_local: bool
    configured: bool

    def cache_key(self) -> tuple[object, ...]:
        return (
            self.provider,
            self.model,
            self.base_url,
            self.api_key,
        )


def list_provider_specs() -> list[dict[str, object]]:
    return [spec.to_public_dict() for spec in PROVIDER_CATALOG]


def get_provider_spec(provider_id: str | None, *, strict: bool = False) -> ProviderSpec:
    clean = (provider_id or "").strip().lower()
    if not clean:
        return PROVIDERS_BY_ID[DEFAULT_PROVIDER_ID]
    spec = PROVIDERS_BY_ID.get(clean)
    if spec is None:
        if strict:
            raise ValueError(f"Provedor desconhecido: '{provider_id}'.")
        return PROVIDERS_BY_ID[DEFAULT_PROVIDER_ID]
    return spec


def normalize_base_url(url: str | None) -> str:
    return (url or "").strip().rstrip("/")


def validate_base_url(url: str | None) -> tuple[bool, str | None]:
    cleaned = normalize_base_url(url)
    if not cleaned:
        return False, "Informe a Base URL do provedor (ex.: https://api.z.ai/api/paas/v4 ou http://localhost:11434/v1)."
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False, "Base URL inválida. Use https:// (ou http:// apenas para servidor local)."
    if parsed.scheme == "http" and not is_loopback_url(cleaned):
        return False, "Use https:// para servidores que não sejam locais."
    return True, None


def is_loopback_url(url: str | None) -> bool:
    cleaned = normalize_base_url(url)
    if not cleaned:
        return False
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower()
    return host in LOOPBACK_HOSTS


def resolve_active_llm_config() -> ActiveLLMConfig:
    """Resolve o provedor ativo a partir das env vars ADITO_LLM_* com fallback legado para Gemini."""
    raw_provider = (os.environ.get("ADITO_LLM_PROVIDER") or "").strip().lower()
    spec = get_provider_spec(raw_provider or DEFAULT_PROVIDER_ID, strict=False)

    env_key = (os.environ.get("ADITO_LLM_API_KEY") or "").strip() or None
    if spec.id == "gemini" and not env_key:
        env_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip() or None

    env_model = (os.environ.get("ADITO_LLM_MODEL") or "").strip()
    if not env_model and spec.id == "gemini":
        env_model = (os.environ.get("GEMINI_MODEL") or "").strip()
    model = env_model or spec.default_model

    env_base_url = normalize_base_url(os.environ.get("ADITO_LLM_BASE_URL"))
    if env_base_url and spec.allow_custom_base_url:
        base_url = env_base_url
    else:
        base_url = spec.base_url

    is_local = spec.protocol == "openai_compatible" and is_loopback_url(base_url)

    if spec.protocol == "gemini":
        configured = bool(env_key)
    else:
        url_ok, _ = validate_base_url(base_url)
        if not url_ok or not model:
            configured = False
        elif is_local:
            configured = True
        else:
            configured = bool(env_key)

    return ActiveLLMConfig(
        provider=spec.id,
        label=spec.label,
        protocol=spec.protocol,
        model=model,
        base_url=base_url,
        api_key=env_key,
        is_local=is_local,
        configured=configured,
    )
