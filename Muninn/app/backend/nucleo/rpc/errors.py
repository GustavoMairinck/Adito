"""Erros que o front recebe com um status no estilo HTTP (o tratamento atual das telas lê status e corpo)."""

import re


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


def llm_error_message(exc: BaseException) -> str | None:
    """Mensagem em português para falhas conhecidas do Gemini (cota, chave, sobrecarga, rede).

    Devolve None quando o erro não é do LLM, para o chamador usar a mensagem genérica.
    """
    texto = f"{exc.__class__.__name__} {exc}".lower()
    codigos = set(re.findall(r"\b[45]\d\d\b", texto))
    if any(sinal in texto for sinal in ("resource_exhausted", "quota", "rate limit", "ratelimit", "too many requests")) or "429" in codigos:
        return (
            "A cota de uso do Gemini acabou. Se for o limite por minuto, tente de novo em alguns instantes; "
            "se for o diário, só volta a liberar amanhã. Você também pode trocar a chave em Configurações."
        )
    if any(sinal in texto for sinal in ("api key not valid", "api_key_invalid", "permission_denied", "unauthenticated")) or codigos & {"401", "403"}:
        return "A chave do Gemini é inválida ou não tem permissão para este modelo. Confira a chave em Configurações."
    if any(sinal in texto for sinal in ("unavailable", "overloaded")) or codigos & {"500", "503"}:
        return "O Gemini está sobrecarregado ou fora do ar no momento. Tente de novo em alguns instantes."
    if any(sinal in texto for sinal in ("timeout", "timed out", "connecterror", "connection", "name resolution")):
        return "Não consegui falar com o Gemini. Verifique a conexão com a internet e tente de novo."
    return None
