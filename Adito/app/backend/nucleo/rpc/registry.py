"""Registro dos métodos que o front pode chamar (`@rpc("nome")`)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Method:
    fn: Callable
    stream: bool  # recebe `emit` e envia eventos antes da resposta final
    is_async: bool


METHODS: dict[str, Method] = {}


def rpc(name: str, stream: bool = False):
    import inspect

    def register(fn):
        METHODS[name] = Method(fn, stream, inspect.iscoroutinefunction(fn))
        return fn

    return register


def load_handlers() -> dict[str, Method]:
    """Importa os módulos de métodos (cada um se registra ao ser importado)."""
    from . import admin, chat, core_methods, dashboard, explorer  # noqa: F401

    return METHODS


async def dispatch(name: str, params: dict, emit=None):
    """Executa um método. Os síncronos (sqlite3, DuckDB) rodam numa thread para não travar o loop."""
    import asyncio

    from .errors import ApiError

    method = METHODS.get(name)
    if method is None:
        raise ApiError(404, {"detail": f"Método desconhecido: {name}"})
    params = params if isinstance(params, dict) else {}
    if method.stream:
        return await method.fn(params, emit)
    if method.is_async:
        return await method.fn(params)
    return await asyncio.to_thread(method.fn, params)
