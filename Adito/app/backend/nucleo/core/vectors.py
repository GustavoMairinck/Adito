"""Vetores em SQLite: guardados como BLOB float32 (core.db) e buscados por força bruta com numpy."""
from typing import Any, Iterable

import numpy as np


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


def embedding_diagnostics(cfg) -> dict[str, object]:
    """Diagnostica suporte e compatibilidade de dimensão/provedor dos vetores persistidos no app.db."""
    from core import db

    dim_counts: dict[int, int] = {}
    stored_providers: set[str] = set()
    provider_mismatch_rows = 0

    for table in ("knowledge_knowledgeitem", "analytics_text_embedding"):
        try:
            for byte_len, total in db.execute(
                f"SELECT LENGTH(embedding), COUNT(*) FROM {table} WHERE embedding IS NOT NULL GROUP BY LENGTH(embedding)"
            ):
                if byte_len and byte_len > 0:
                    dim = int(byte_len // 4)
                    dim_counts[dim] = dim_counts.get(dim, 0) + int(total)
        except Exception:
            continue

    try:
        for provider, total in db.execute(
            "SELECT COALESCE(json_extract(metadata, '$.embedding_provider'), ''), COUNT(*) "
            "FROM knowledge_knowledgeitem WHERE embedding IS NOT NULL "
            "GROUP BY COALESCE(json_extract(metadata, '$.embedding_provider'), '')"
        ):
            clean = str(provider or "").strip().lower()
            if clean:
                stored_providers.add(clean)
                if clean != cfg.provider:
                    provider_mismatch_rows += int(total)
    except Exception:
        pass

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

    incompatible_by_dim = 0
    if expected_dim is not None:
        incompatible_by_dim = sum(count for dim, count in dim_counts.items() if dim != expected_dim)
    elif len(stored_dims) > 1:
        # Dimensão esperada desconhecida (ex.: modelo custom/Z.AI), mas há mistura no banco.
        dominant = max(dim_counts.values())
        incompatible_by_dim = sum(dim_counts.values()) - dominant

    incompatible_vectors = max(incompatible_by_dim, provider_mismatch_rows)
    needs_retrain = bool(
        incompatible_vectors > 0
        or len(stored_dims) > 1
        or any(p != cfg.provider for p in stored_providers)
    )

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
