"""Embeddings com o provedor ativo do usuário (carga de contextos e comandos de manutenção).

Limites por minuto (HTTP 429 / rate limit) fazem o embedder esperar o tempo solicitado e tentar de novo.
Cota diária esgotada não adianta esperar: vira CotaEsgotada com uma mensagem clara.
"""
import logging
import re
import time

from agents.config import get_embeddings
from agents.providers import resolve_active_llm_config

logger = logging.getLogger(__name__)

ESPERA_PADRAO = 30.0   # segundos, quando o provedor não informa quanto esperar
ESPERA_MAXIMA = 90.0
TENTATIVAS = 8


class EmbedderIndisponivel(RuntimeError):
    pass


class CotaEsgotada(RuntimeError):
    pass


def _e_limite(exc: Exception) -> bool:
    texto = str(exc)
    lower = texto.lower()
    return (
        "429" in texto
        or "RESOURCE_EXHAUSTED" in texto
        or "rate_limit" in lower
        or "rate limit" in lower
        or "too many requests" in lower
    )


def _e_limite_diario(exc: Exception) -> bool:
    return bool(re.search(r"per\s*day|PerDay|daily", str(exc), re.IGNORECASE))


def _espera_pedida(exc: Exception) -> float:
    """Provedores como Gemini/OpenAI enviam 'retryDelay': '34s' ou 'Please retry in 33.9s'."""
    texto = str(exc)
    achado = (
        re.search(r"retry (?:after|in) ([\d.]+)\s*s", texto, re.IGNORECASE)
        or re.search(r"retryDelay['\"]?\s*:\s*['\"]?([\d.]+)s", texto)
    )
    if achado:
        return min(float(achado.group(1)) + 1, ESPERA_MAXIMA)
    return ESPERA_PADRAO


class EmbedderComEspera:
    """Repassa embed_documents/embed_query ao embedder real, esperando em limites temporários (429)."""

    def __init__(self, embedder, dormir=time.sleep, tentativas: int = TENTATIVAS, provider_label: str | None = None):
        self._embedder = embedder
        self._dormir = dormir
        self._tentativas = tentativas
        self._provider_label = provider_label or resolve_active_llm_config().label

    def _com_espera(self, funcao, *args, **kwargs):
        for tentativa in range(1, self._tentativas + 1):
            try:
                return funcao(*args, **kwargs)
            except Exception as exc:
                if not _e_limite(exc):
                    raise
                if _e_limite_diario(exc):
                    raise CotaEsgotada(
                        f"A cota diária do provedor {self._provider_label} acabou. O que já foi indexado está salvo; "
                        "carregue os contextos de novo amanhã para continuar."
                    ) from exc
                if tentativa == self._tentativas:
                    raise CotaEsgotada(
                        f"O provedor {self._provider_label} continuou recusando por limite de uso depois de "
                        f"{self._tentativas} tentativas. O que já foi indexado está salvo; "
                        "carregue os contextos de novo para continuar."
                    ) from exc
                espera = _espera_pedida(exc)
                logger.warning(
                    "Limite por minuto em %s; esperando %.0fs (tentativa %d de %d).",
                    self._provider_label,
                    espera,
                    tentativa,
                    self._tentativas,
                )
                self._dormir(espera)

    def embed_documents(self, texts, *args, **kwargs):
        return self._com_espera(self._embedder.embed_documents, texts, *args, **kwargs)

    def embed_query(self, text, *args, **kwargs):
        return self._com_espera(self._embedder.embed_query, text, *args, **kwargs)


def get_embedder():
    cfg = resolve_active_llm_config()
    if not cfg.configured:
        raise EmbedderIndisponivel(f"Provedor {cfg.label} não configurado.")
    if not cfg.supports_embeddings:
        raise EmbedderIndisponivel(f"O provedor {cfg.label} não oferece suporte a embeddings.")
    embedder = get_embeddings()
    if embedder is None:
        raise EmbedderIndisponivel(f"Embedder indisponível para o provedor {cfg.label}.")
    return EmbedderComEspera(embedder, provider_label=cfg.label)
