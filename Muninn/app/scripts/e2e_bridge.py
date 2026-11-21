"""Ponte HTTP local (uso exclusivo em testes E2E live) entre o Playwright e o núcleo Python real.

Inicia o `desktop_server.py` contra um `MUNINN_DATA_DIR` isolado contendo o `dados.db` real
e o contexto `pesquisa-extensao-ifes`, expondo `/health` e `/rpc` em `127.0.0.1:<porta>`.

Uso:
    .venv/bin/python scripts/e2e_bridge.py --port 18765
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
NUCLEO_DIR = APP_DIR / "backend" / "nucleo"
DEFAULT_BANCO = APP_DIR / "data" / "dados.db"
DEFAULT_CONTEXT_SRC = APP_DIR / "contexts" / "pesquisa-extensao-ifes"


class CoreBridge:
    def __init__(self, banco_path: Path) -> None:
        self.data_dir = Path(tempfile.mkdtemp(prefix="muninn-e2e-live-"))
        target_db = self.data_dir / "dados.db"
        try:
            os.symlink(banco_path.resolve(), target_db)
        except OSError:
            shutil.copy2(banco_path, target_db)

        if DEFAULT_CONTEXT_SRC.is_dir():
            shutil.copytree(DEFAULT_CONTEXT_SRC, self.data_dir / "contexts" / DEFAULT_CONTEXT_SRC.name)

        env = {**os.environ, "MUNINN_DATA_DIR": str(self.data_dir), "PYTHONUNBUFFERED": "1"}
        env["GEMINI_API_KEY"] = ""
        env["GOOGLE_API_KEY"] = ""

        self.log_file = open(self.data_dir / "e2e_nucleo.log", "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, str(NUCLEO_DIR / "desktop_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_file,
            env=env,
            text=True,
            encoding="utf-8",
        )
        self.lock = threading.Lock()
        self.next_id = 0

        assert self.proc.stdout is not None
        ready_line = self.proc.stdout.readline()
        if not ready_line:
            raise RuntimeError("Núcleo encerrou antes do evento ready.")
        ready = json.loads(ready_line)
        if ready.get("event") != "ready":
            raise RuntimeError(f"Evento inicial inesperado: {ready}")

    def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            assert self.proc.stdin is not None and self.proc.stdout is not None
            self.next_id += 1
            rid = self.next_id
            self.proc.stdin.write(json.dumps({"id": rid, "method": method, "params": params}) + "\n")
            self.proc.stdin.flush()
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    raise EOFError("stdout do núcleo fechado")
                msg = json.loads(line)
                if msg.get("id") == rid and "ok" in msg:
                    return msg

    def close(self) -> None:
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        finally:
            self.log_file.close()
            shutil.rmtree(self.data_dir, ignore_errors=True)


def make_handler(bridge: CoreBridge):
    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                body = json.dumps({"status": "ok"}).encode("utf-8")
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/rpc":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            resp = bridge.call(str(payload.get("method", "")), payload.get("params") or {})
            body = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge HTTP local para testes E2E live do Muninn.")
    parser.add_argument("--banco", type=Path, default=DEFAULT_BANCO)
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()

    if not args.banco.is_file():
        print(f"❌ Erro: banco SQLite não encontrado em '{args.banco}'. Execute 'make db' primeiro.", file=sys.stderr)
        return 2

    bridge = CoreBridge(args.banco)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(bridge))

    def shutdown(*_args: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(f"E2E_BRIDGE_READY http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
