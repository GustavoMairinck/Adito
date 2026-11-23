"""Adaptador do teste de contrato: chama o núcleo local direto pelo despacho de métodos."""
from __future__ import annotations

import json


class Rpc:
    """Núcleo local (rpc/), chamado direto pelo despacho, sem o processo e o stdin/stdout."""

    def __init__(self):
        from langchain_core.embeddings.fake import DeterministicFakeEmbedding

        import rpc.admin
        from rpc.server import startup

        startup()
        rpc.admin.get_embedder = lambda: DeterministicFakeEmbedding(size=1024)

    async def call(self, method, params):
        from rpc.errors import ApiError
        from rpc.jsonio import dumps
        from rpc.registry import dispatch

        try:
            result = await dispatch(method, dict(params))
        except ApiError as exc:
            return exc.status, json.loads(dumps(exc.data))
        return 200, json.loads(dumps(result))

    async def stream(self, method, params, get_graph):
        import rpc.chat
        from rpc.errors import ApiError
        from rpc.jsonio import dumps
        from rpc.registry import dispatch

        rpc.chat.get_graph = get_graph
        events = []

        async def emit(event, data):
            events.append({"event": event, "data": json.loads(dumps(data))})

        try:
            await dispatch(method, dict(params), emit)
        except ApiError as exc:
            return exc.status, [{"event": "http", "data": exc.data}]
        return 200, events


def adaptador(nome: str):
    # A referência foi gravada com o servidor Django (adaptador "atual"), antes de ele ser removido.
    if nome == "rpc":
        return Rpc()
    raise SystemExit(f"Implementação desconhecida: {nome}")
