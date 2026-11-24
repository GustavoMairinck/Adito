"""Erros que o front recebe com um status no estilo HTTP (o tratamento atual das telas lê status e corpo)."""

import re

import httpx

from agents.providers import resolve_active_llm_config


class ApiError(Exception):
    def __init__(self, status: int, data):
        super().__init__(f"{status}: {data}")
        self.status = status
        self.data = data


def bad_request(data) -> ApiError:
    return ApiError(400, data)


def not_found(what: str) -> ApiError:
    return ApiError(404, {"detail": f"No {what} matches the given query."})


def forbidden(detail: str) -> ApiError:
    return ApiError(403, {"detail": detail})


def _provider_label() -> str:
    return resolve_active_llm_config().label


def cota_esgotada_message(label: str | None = None) -> str:
    nome = label or _provider_label()
    return (
        f"A cota de uso do {nome} acabou. Se for o limite por minuto, tente de novo em alguns instantes; "
        "se for o diário, só volta a liberar amanhã. Você também pode trocar o provedor ou a chave em Configurações."
    )


def chave_invalida_message(label: str | None = None) -> str:
    nome = label or _provider_label()
    return f"A chave do {nome} é inválida ou não tem permissão para este modelo. Confira a chave em Configurações."


def capacidade_plano_message(label: str | None = None, model: str | None = None) -> str:
    cfg = resolve_active_llm_config()
    nome = label or cfg.label
    modelo = model or cfg.model
    return (
        f"O modelo '{modelo}' está sem capacidade disponível no plano atual da {nome} (HTTP 429). "
        "Tente novamente em instantes ou escolha outro modelo em Configurações."
    )


def sobrecarga_message(label: str | None = None) -> str:
    nome = label or _provider_label()
    return f"O provedor {nome} está sobrecarregado ou fora do ar no momento. Tente de novo em alguns instantes."


def rede_message(label: str | None = None, base_url: str | None = None, is_local: bool | None = None) -> str:
    cfg = resolve_active_llm_config()
    nome = label or cfg.label
    local = cfg.is_local if is_local is None else is_local
    url = base_url or cfg.base_url
    if local:
        return f"Não consegui conectar ao servidor local ({url}). Verifique se o {nome} está rodando e tente de novo."
    return f"Não consegui falar com o {nome}. Verifique a conexão com a internet e tente de novo."


def modelo_nao_encontrado_message(label: str | None = None, model: str | None = None) -> str:
    cfg = resolve_active_llm_config()
    nome = label or cfg.label
    modelo = model or cfg.model
    return f"O modelo '{modelo}' não foi encontrado em {nome}. Confira o nome do modelo em Configurações."


def structured_output_message(label: str | None = None) -> str:
    nome = label or _provider_label()
    return (
        f"O modelo configurado em {nome} não suporta saída estruturada (tool calling). "
        "Escolha outro modelo compatível em Configurações."
    )


COTA_ESGOTADA = cota_esgotada_message("Gemini")

# Textos que os SDKs/APIs (Gemini, OpenAI e OpenAI-compatíveis) usam de fato; nada de números soltos.
_MARCAS_COTA = (
    "resource_exhausted",
    "quota",
    "insufficient_quota",
    "rate limit",
    "rate_limit_exceeded",
    "ratelimit",
    "too many requests",
)
_MARCAS_CHAVE = (
    "api key not valid",
    "api_key_invalid",
    "invalid_api_key",
    "incorrect api key",
    "authentication_error",
    "permission_denied",
    "unauthenticated",
    "unauthorized",
)
_MARCAS_MODELO = (
    "model_not_found",
    "not found for api version",
    "does not exist or you do not have access",
)
_MARCAS_STRUCTURED = (
    "does not support tools",
    "does not support function",
    "tool calling is not supported",
    "function calling is not supported",
    "tool_choice is not supported",
)
_MARCAS_SOBRECARGA = ("service unavailable", "internal server error", "model is overloaded", "overloaded")
# Status só com rótulo ("HTTP 429", "Status: 503", sem diferenciar maiúsculas) ou no começo seguido de
# um nome de erro em caixa alta ("503 UNAVAILABLE"); assim "500 linhas" não conta.
_STATUS_NO_TEXTO = re.compile(
    r"(?i:\b(?:status(?:[_ ]code)?|http(?:/\d(?:\.\d)?)?|code)\W{0,3}(\d{3})\b)|^\s*(\d{3})\s+[A-Z_]{4,}\b"
)


def _cadeia(exc: BaseException):
    """A exceção e suas causas (`raise ... from`), sem repetir nem entrar em laço."""
    vistos = []
    while exc is not None and all(exc is not v for v in vistos) and len(vistos) < 6:
        vistos.append(exc)
        exc = exc.__cause__ or exc.__context__
    return vistos


def _status_http(exc: BaseException) -> int | None:
    """Status HTTP declarado pela própria exceção (SDK do Google, OpenAI, httpx, requests), se houver."""
    for atributo in ("status_code", "code"):
        valor = getattr(exc, atributo, None)
        if isinstance(valor, int) and 400 <= valor <= 599:
            return valor
    resposta = getattr(exc, "response", None)
    valor = getattr(resposta, "status_code", None)
    return valor if isinstance(valor, int) else None


def is_cota_message(msg: str | None) -> bool:
    return bool(msg and "cota" in msg.lower())


def llm_error_message(exc: BaseException) -> str | None:
    """Mensagem em português para falhas conhecidas do provedor de IA (cota, chave, modelo, sobrecarga, rede).

    Devolve None quando o erro não parece ser do LLM, para o chamador usar a mensagem genérica.
    Só reconhece o que o SDK/API declara (status da exceção, nomes de erro dos provedores, falhas de rede do
    httpx); um número solto ou a palavra "connection" num erro local (SQLite, SQL) não conta.
    """
    cfg = resolve_active_llm_config()
    for erro in _cadeia(exc):
        status = _status_http(erro)
        texto = f"{erro.__class__.__name__} {erro}".lower()
        if not status:
            achado = _STATUS_NO_TEXTO.search(str(erro))
            status = int(achado.group(1) or achado.group(2)) if achado else None
        if "service tier capacity exceeded" in texto or "capacity exceeded" in texto:
            return capacidade_plano_message(cfg.label, cfg.model)
        if status == 429 or any(marca in texto for marca in _MARCAS_COTA):
            return cota_esgotada_message(cfg.label)
        if status in (401, 403) or any(marca in texto for marca in _MARCAS_CHAVE):
            return chave_invalida_message(cfg.label)
        if any(marca in texto for marca in _MARCAS_STRUCTURED):
            return structured_output_message(cfg.label)
        if status == 404 or any(marca in texto for marca in _MARCAS_MODELO):
            return modelo_nao_encontrado_message(cfg.label, cfg.model)
        if status in (500, 502, 503, 504) or any(marca in texto for marca in _MARCAS_SOBRECARGA):
            return sobrecarga_message(cfg.label)
        if isinstance(erro, (httpx.TransportError, ConnectionError, TimeoutError)):
            return rede_message(cfg.label, cfg.base_url, cfg.is_local)
    return None
