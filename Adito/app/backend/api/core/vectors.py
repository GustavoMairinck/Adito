"""Vetores em SQLite: guardados como BLOB float32 (core.db) e buscados por força bruta com numpy."""
from typing import Any, Iterable

import numpy as np


def to_blob(vector: Any) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob: bytes | memoryview) -> np.ndarray:
    return np.frombuffer(bytes(blob), dtype=np.float32)


def nearest(items: Iterable[Any], query: Any, k: int, attr: str = "embedding") -> list[tuple[Any, float]]:
    """Os k itens mais próximos por distância L2 (mesma métrica do pgvector L2Distance)."""
    candidates = [item for item in items if getattr(item, attr) is not None]
    if not candidates or k <= 0:
        return []
    matrix = np.vstack([getattr(item, attr) for item in candidates])
    distances = np.linalg.norm(matrix - np.asarray(query, dtype=np.float32), axis=1)
    order = np.argsort(distances)[:k]
    return [(candidates[i], float(distances[i])) for i in order]
