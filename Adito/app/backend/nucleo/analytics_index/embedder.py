"""Embeddings com a chave do usuário (usado pela carga de contextos e pelos comandos de manutenção).

A cota gratuita do Gemini limita os pedidos por minuto. Indexar um contexto inteiro passa desse
limite, então um 429 por minuto faz o embedder esperar o tempo que o Gemini pede e tentar de novo.
Cota diária esgotada não adianta esperar: vira CotaEsgotada com uma mensagem clara.
"""
import logging
import re
import time

from agents.config import get_embeddings, get_gemini_api_key

logger = logging.getLogger(__name__)

ESPERA_PADRAO = 30.0   # segundos, quando o Gemini não diz quanto esperar
ESPERA_MAXIMA = 90.0
TENTATIVAS = 8


class EmbedderIndisponivel(RuntimeError):
    pass


class CotaEsgotada(RuntimeError):
    pass


def _e_limite(exc: Exception) -> bool:
    texto = str(exc)
    return "429" in texto or "RESOURCE_EXHAUSTED" in texto


def _e_limite_diario(exc: Exception) -> bool:
    return bool(re.search(r"per\s*day|PerDay", str(exc), re.IGNORECASE))


def _espera_pedida(exc: Exception) -> float:
    """O Gemini manda 'retryDelay': '34s' ou 'Please retry in 33.9s'."""
    texto = str(exc)
    achado = re.search(r"retry in ([\d.]+)\s*s", texto, re.IGNORECASE) or re.search(r"retryDelay['\"]?\s*:\s*['\"]?([\d.]+)s", texto)
    if achado:
        return min(float(achado.group(1)) + 1, ESPERA_MAXIMA)
    return ESPERA_PADRAO


class EmbedderComEspera:
    """Repassa embed_documents/embed_query ao embedder real, esperando quando o Gemini pede."""

    def __init__(self, embedder, dormir=time.sleep, tentativas: int = TENTATIVAS):
        self._embedder = embedder
        self._dormir = dormir
        self._tentativas = tentativas

    def _com_espera(self, funcao, *args, **kwargs):
        for tentativa in range(1, self._tentativas + 1):
            try:
                return funcao(*args, **kwargs)
            except Exception as exc:
                if not _e_limite(exc):
                    raise
                if _e_limite_diario(exc):
                    raise CotaEsgotada(
                        "A cota diária da chave do Gemini acabou. O que já foi indexado está salvo; "
                        "carregue os contextos de novo amanhã para continuar."
                    ) from exc
                if tentativa == self._tentativas:
                    raise CotaEsgotada(
                        f"O Gemini continuou recusando por limite de uso depois de {self._tentativas} tentativas. "
                        "O que já foi indexado está salvo; carregue os contextos de novo para continuar."
                    ) from exc
                espera = _espera_pedida(exc)
                logger.warning("Limite por minuto do Gemini; esperando %.0fs (tentativa %d de %d).", espera, tentativa, self._tentativas)
                self._dormir(espera)

    def embed_documents(self, texts, *args, **kwargs):
        return self._com_espera(self._embedder.embed_documents, texts, *args, **kwargs)

    def embed_query(self, text, *args, **kwargs):
        return self._com_espera(self._embedder.embed_query, text, *args, **kwargs)


def get_embedder():
    if not get_gemini_api_key():
        raise EmbedderIndisponivel("GEMINI_API_KEY não configurada.")
    return EmbedderComEspera(get_embeddings())
