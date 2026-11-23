"""Erros que o front recebe com um status no estilo HTTP (o tratamento atual das telas lê status e corpo)."""

import re

import httpx


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


_COTA = (
    "A cota de uso do Gemini acabou. Se for o limite por minuto, tente de novo em alguns instantes; "
    "se for o diário, só volta a liberar amanhã. Você também pode trocar a chave em Configurações."
)
COTA_ESGOTADA = _COTA
_CHAVE = "A chave do Gemini é inválida ou não tem permissão para este modelo. Confira a chave em Configurações."
_SOBRECARGA = "O Gemini está sobrecarregado ou fora do ar no momento. Tente de novo em alguns instantes."
_REDE = "Não consegui falar com o Gemini. Verifique a conexão com a internet e tente de novo."

# Textos que o SDK/API do Gemini usa de fato; nada de números soltos, que também aparecem em erros locais.
_MARCAS_COTA = ("resource_exhausted", "quota", "rate limit", "ratelimit", "too many requests")
_MARCAS_CHAVE = ("api key not valid", "api_key_invalid", "permission_denied", "unauthenticated")
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
    """Status HTTP declarado pela própria exceção (SDK do Google, httpx, requests), se houver."""
    for atributo in ("status_code", "code"):
        valor = getattr(exc, atributo, None)
        if isinstance(valor, int) and 400 <= valor <= 599:
            return valor
    resposta = getattr(exc, "response", None)
    valor = getattr(resposta, "status_code", None)
    return valor if isinstance(valor, int) else None


def llm_error_message(exc: BaseException) -> str | None:
    """Mensagem em português para falhas conhecidas do Gemini (cota, chave, sobrecarga, rede).

    Devolve None quando o erro não parece ser do LLM, para o chamador usar a mensagem genérica.
    Só reconhece o que o SDK/API declara (status da exceção, nomes de erro do Gemini, falhas de rede do
    httpx); um número solto ou a palavra "connection" num erro local (SQLite, SQL) não conta.
    """
    for erro in _cadeia(exc):
        status = _status_http(erro)
        texto = f"{erro.__class__.__name__} {erro}".lower()
        if not status:
            achado = _STATUS_NO_TEXTO.search(str(erro))
            status = int(achado.group(1) or achado.group(2)) if achado else None
        if status == 429 or any(marca in texto for marca in _MARCAS_COTA):
            return _COTA
        if status in (401, 403) or any(marca in texto for marca in _MARCAS_CHAVE):
            return _CHAVE
        if status in (500, 503) or any(marca in texto for marca in _MARCAS_SOBRECARGA):
            return _SOBRECARGA
        if isinstance(erro, (httpx.TransportError, ConnectionError, TimeoutError)):
            return _REDE
    return None
