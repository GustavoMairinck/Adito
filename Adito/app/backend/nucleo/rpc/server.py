"""
Núcleo local do Adito falando com o Tauri por stdin/stdout, uma mensagem JSON por linha.

Pedido     (Tauri → núcleo): {"id": 7, "method": "dashboard.kpis", "params": {...}}
Resposta   (núcleo → Tauri): {"id": 7, "ok": true, "result": ...}
Erro                         {"id": 7, "ok": false, "error": {"status": 404, "data": {...}}}
Evento de stream             {"id": 7, "event": "token", "data": {...}}   (antes da resposta)
Cancelar                     {"method": "$cancel", "params": {"id": 7}}
Pronto                       {"event": "ready", "data": {...}}            (uma vez, ao subir)

O stdout real fica reservado ao protocolo: o descritor 1 passa a apontar para o stderr, então
um print() de qualquer biblioteca vai para o log, não para o canal. Quando o app fecha (ou morre),
o stdin chega ao fim e o núcleo encerra.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time

from .errors import ApiError
from .jsonio import dumps

logger = logging.getLogger("adito.rpc")


def reserve_stdout():
    """Devolve um arquivo para o protocolo e manda o resto do stdout para o stderr."""
    proto = os.fdopen(os.dup(1), "w", encoding="utf-8", newline="\n")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return proto


class Server:
    def __init__(self, out):
        self.out = out
        self.write_lock = threading.Lock()
        self.tasks: dict = {}

    def send(self, message: dict) -> None:
        line = dumps(message) + "\n"
        with self.write_lock:
            self.out.write(line)
            self.out.flush()

    async def run_request(self, rid, method: str, params: dict) -> None:
        from .registry import dispatch

        async def emit(event: str, data) -> None:
            self.send({"id": rid, "event": event, "data": data})

        t0 = time.monotonic()
        try:
            result = await dispatch(method, params, emit)
            self.send({"id": rid, "ok": True, "result": result})
        except ApiError as exc:
            self.send({"id": rid, "ok": False, "error": {"status": exc.status, "data": exc.data}})
        except asyncio.CancelledError:
            self.send({"id": rid, "ok": False, "error": {"status": 499, "data": {"detail": "Cancelado."}}})
        except Exception as exc:  # erro inesperado: vai para o log e o front recebe 500
            logger.exception("Erro em %s", method)
            self.send({"id": rid, "ok": False, "error": {"status": 500, "data": {"detail": str(exc) or exc.__class__.__name__}}})
        finally:
            logger.debug("%s %s %.0f ms", rid, method, (time.monotonic() - t0) * 1000)

    def handle(self, message: dict) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        if method == "$cancel":
            task = self.tasks.get(params.get("id"))
            if task:
                task.cancel()
            return
        rid = message.get("id")
        task = asyncio.create_task(self.run_request(rid, method, params))
        self.tasks[rid] = task
        task.add_done_callback(lambda t, rid=rid: self._done(rid, t))

    def _done(self, rid, task) -> None:
        self.tasks.pop(rid, None)
        # Cancelado antes de começar a rodar: run_request nem chegou a responder.
        if task.cancelled():
            self.send({"id": rid, "ok": False, "error": {"status": 499, "data": {"detail": "Cancelado."}}})

    async def serve(self, stdin) -> None:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def reader():
            for raw in stdin:
                loop.call_soon_threadsafe(queue.put_nowait, raw)
            loop.call_soon_threadsafe(queue.put_nowait, None)  # fim do stdin: o app fechou

        threading.Thread(target=reader, name="stdin", daemon=True).start()
        while (raw := await queue.get()) is not None:
            try:
                message = json.loads(raw)
            except ValueError:
                logger.warning("Linha inválida ignorada: %r", raw[:200])
                continue
            self.handle(message)
        for task in list(self.tasks.values()):
            task.cancel()


def startup() -> dict:
    """Prepara o app.db, o usuário local e os contextos; devolve o que vai no evento ready."""
    from core.contexts import sync_default_contexts
    from core.schema import ensure_schema

    from .registry import load_handlers
    from .session import current

    versao = ensure_schema()
    _, tenant = current()
    if tenant:
        sync_default_contexts(tenant)
    methods = load_handlers()
    return {"schema": versao, "methods": len(methods)}


def main() -> None:
    proto = reserve_stdout()
    logging.basicConfig(
        level=os.environ.get("ADITO_LOG_LEVEL", "INFO"),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    server = Server(proto)
    t0 = time.monotonic()
    try:
        info = startup()
    except Exception as exc:
        logger.exception("Falha ao iniciar o núcleo")
        server.send({"event": "fatal", "data": {"message": str(exc) or exc.__class__.__name__}})
        sys.exit(1)
    info["startup_ms"] = round((time.monotonic() - t0) * 1000)
    server.send({"event": "ready", "data": info})
    logger.info("Núcleo pronto em %s ms", info["startup_ms"])

    async def run():
        try:
            await server.serve(sys.stdin.buffer)
        finally:
            from agents.orchestrator.graph import close_graph
            from core.datastore import close_dados

            await close_graph()
            close_dados()

    asyncio.run(run())
