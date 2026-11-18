"""Embeddings com a chave do usuário (usado pela carga de contextos e pelos comandos de manutenção)."""
from agents.config import get_embeddings, get_gemini_api_key


class EmbedderIndisponivel(RuntimeError):
    pass


def get_embedder():
    if not get_gemini_api_key():
        raise EmbedderIndisponivel("GEMINI_API_KEY não configurada.")
    return get_embeddings()
