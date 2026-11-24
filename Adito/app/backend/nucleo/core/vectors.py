"""Vetores em SQLite: guardados como BLOB float32 (core.db) e buscados por força bruta com numpy."""
import logging
from typing import Any, Iterable

import numpy as np

from agents.providers import ActiveLLMConfig

logger = logging.getLogger(__name__)


def to_blob(vector: Any) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob: bytes | memoryview) -> np.ndarray:
    return np.frombuffer(bytes(blob), dtype=np.float32)


def nearest_with_stats(
    items: Iterable[Any],
    query: Any,
    k: int,
    attr: str = "embedding",
) -> tuple[list[tuple[Any, float]], int]:
    """Os k itens mais próximos por distância L2, ignorando com segurança vetores de dimensão incompatível."""
    query_vec = np.asarray(query, dtype=np.float32).reshape(-1)
    query_dim = query_vec.shape[0]
    compatible_items: list[Any] = []
    compatible_vecs: list[np.ndarray] = []
    incompatible = 0

    for item in items:
        raw = getattr(item, attr)
        if raw is None:
            continue
        vec = np.asarray(raw, dtype=np.float32).reshape(-1)
        if vec.shape[0] != query_dim:
            incompatible += 1
            continue
        compatible_items.append(item)
        compatible_vecs.append(vec)

    if not compatible_items or k <= 0:
        return [], incompatible

    matrix = np.vstack(compatible_vecs)
    distances = np.linalg.norm(matrix - query_vec, axis=1)
    order = np.argsort(distances)[:k]
    return [(compatible_items[i], float(distances[i])) for i in order], incompatible


def nearest(items: Iterable[Any], query: Any, k: int, attr: str = "embedding") -> list[tuple[Any, float]]:
    """Os k itens mais próximos por distância L2 (mesma métrica do pgvector L2Distance)."""
    matches, _ = nearest_with_stats(items, query, k, attr=attr)
    return matches


def vector_matches_provider(
    stored_provider: str | None,
    stored_model: str | None,
    cfg: ActiveLLMConfig,
) -> bool:
    """Confere se um vetor pertence ao provedor/modelo ativo.

    Vetores legados sem tag (criados na v0.1.0) são assumidos como Gemini; ao usar outro provedor
    são considerados incompatíveis para evitar misturar espaços vetoriais de mesma dimensão (ex.: 1024).
    """
    prov = (stored_provider or "").strip().lower()
    model = (stored_model or "").strip()
    if not prov:
        return cfg.provider == "gemini"
    if prov != cfg.provider:
        return False
    if model and cfg.embedding_model and model != cfg.embedding_model:
        return False
    return True


def embedding_diagnostics(cfg: ActiveLLMConfig) -> dict[str, object]:
    """Diagnostica suporte e compatibilidade de dimensão, provedor e modelo dos vetores no app.db."""
    from core import db

    dim_counts: dict[int, int] = {}
    incompatible_vectors = 0
    needs_retrain = False

    def _accumulate(byte_len: int | None, prov: str | None, model: str | None, total: int) -> None:
        nonlocal incompatible_vectors, needs_retrain
        if not byte_len or byte_len <= 0:
            return
        dim = int(byte_len // 4)
        dim_counts[dim] = dim_counts.get(dim, 0) + int(total)
        if not cfg.supports_embeddings:
            return
        dim_mismatch = cfg.embedding_dim is not None and dim != cfg.embedding_dim
        prov_mismatch = not vector_matches_provider(prov, model, cfg)
        if dim_mismatch or prov_mismatch:
            incompatible_vectors += int(total)
            needs_retrain = True

    try:
        for byte_len, prov, model, total in db.execute(
            "SELECT LENGTH(embedding), "
            "COALESCE(json_extract(metadata, '$.embedding_provider'), ''), "
            "COALESCE(json_extract(metadata, '$.embedding_model'), ''), "
            "COUNT(*) "
            "FROM knowledge_knowledgeitem WHERE embedding IS NOT NULL "
            "GROUP BY LENGTH(embedding), "
            "COALESCE(json_extract(metadata, '$.embedding_provider'), ''), "
            "COALESCE(json_extract(metadata, '$.embedding_model'), '')"
        ):
            _accumulate(byte_len, prov, model, total)
    except Exception as exc:
        logger.warning("Falha ao diagnosticar embeddings em knowledge_knowledgeitem: %s", exc)

    try:
        for byte_len, prov, model, total in db.execute(
            "SELECT LENGTH(embedding), "
            "COALESCE(embedding_provider, ''), "
            "COALESCE(embedding_model, ''), "
            "COUNT(*) "
            "FROM analytics_text_embedding WHERE embedding IS NOT NULL "
            "GROUP BY LENGTH(embedding), COALESCE(embedding_provider, ''), COALESCE(embedding_model, '')"
        ):
            _accumulate(byte_len, prov, model, total)
    except Exception as exc:
        logger.warning("Falha ao diagnosticar embeddings em analytics_text_embedding: %s", exc)

    stored_dims = sorted(dim_counts.keys())
    expected_dim = cfg.embedding_dim

    if not cfg.supports_embeddings:
        return {
            "supports_embeddings": False,
            "provider": cfg.provider,
            "provider_label": cfg.label,
            "embedding_model": None,
            "expected_dim": None,
            "stored_dims": stored_dims,
            "needs_retrain": False,
            "incompatible_vectors": 0,
        }

    if len(stored_dims) > 1:
        needs_retrain = True
        if incompatible_vectors == 0:
            # Dimensão esperada desconhecida (ex.: modelo custom/Z.AI) e mesma tag, mas há mistura de dimensões.
            incompatible_vectors = sum(dim_counts.values()) - max(dim_counts.values())

    return {
        "supports_embeddings": True,
        "provider": cfg.provider,
        "provider_label": cfg.label,
        "embedding_model": cfg.embedding_model,
        "expected_dim": expected_dim,
        "stored_dims": stored_dims,
        "needs_retrain": needs_retrain,
        "incompatible_vectors": incompatible_vectors,
    }
