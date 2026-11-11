"""Vetores em SQLite: guardados como BLOB float32 e buscados por força bruta com numpy."""
from typing import Any, Iterable

import numpy as np
from django.db import models


class EmbeddingField(models.BinaryField):
    """BinaryField que aceita lista/ndarray na escrita e devolve ndarray float32 na leitura."""

    def __init__(self, *args, dimensions: int | None = None, **kwargs):
        self.dimensions = dimensions
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions
        return name, path, args, kwargs

    def get_prep_value(self, value):
        if value is None or isinstance(value, (bytes, bytearray, memoryview)):
            return super().get_prep_value(value)
        return super().get_prep_value(to_blob(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return from_blob(value)

    def to_python(self, value):
        if value is None or isinstance(value, np.ndarray):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            return from_blob(value)
        return np.asarray(value, dtype=np.float32)


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
