"""Teste do processo do núcleo por stdin/stdout, como o Tauri o usa (sem LLM e sem rede).

Verifica: evento ready, pedidos concorrentes, erro com status, cancelamento, linha inválida,
nada além do protocolo no stdout e saída do processo quando o stdin fecha.

Uso (de Adito/app):
    .venv/bin/python scripts/teste_stdio.py
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

ok, falhas = 0, []


def check(nome, cond, detalhe=""):
    global ok
    if cond:
        ok += 1
        print(f"  OK   {nome}")
    else:
        falhas.append(nome)
        print(f"  FALHA {nome} {detalhe}")


class Nucleo:
    def __init__(self, data_dir: Path):
        env = {**os.environ, "ADITO_DATA_DIR": str(data_dir), "PYTHONUNBUFFERED": "1"}
        env["GEMINI_API_KEY"] = ""
        env["GOOGLE_API_KEY"] = ""
        self.t0 = time.monotonic()
        self.proc = subprocess.Popen(
            [sys.executable, str(APP_DIR / "backend" / "nucleo" / "desktop_server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(data_dir / "nucleo.log", "w"),
            env=env, cwd=str(data_dir), text=True, encoding="utf-8",
        )
        self.next_id = 0

    def read(self) -> dict:
        line = self.proc.stdout.readline()
        if not line:
            raise EOFError("stdout fechado")
        return json.loads(line)

    def send(self, message: dict) -> None:
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params=None) -> int:
        self.next_id += 1
        self.send({"id": self.next_id, "method": method, "params": params or {}})
        return self.next_id

    def call(self, method: str, params=None) -> dict:
        rid = self.request(method, params)
        while True:
            msg = self.read()
            if msg.get("id") == rid and "ok" in msg:
                return msg


def main() -> int:
    import teste_contrato

    data_dir = Path(tempfile.mkdtemp(prefix="adito-stdio-"))
    teste_contrato.DATA_DIR = data_dir
    teste_contrato.criar_dados()
    try:
        print("[1] Início")
        n = Nucleo(data_dir)
        ready = n.read()
        startup = time.monotonic() - n.t0
        check("primeira linha é o evento ready", ready.get("event") == "ready", ready)
        print(f"       pronto em {startup:.2f} s (núcleo: {ready.get('data', {}).get('startup_ms')} ms)")

        print("[2] Chamadas")
        check("health", n.call("health")["result"] == {"status": "ok"})
        me = n.call("me")
        check("me sem chave", me["ok"] and me["result"]["llm_configured"] is False, me)
        ctxs = n.call("contextos.list")["result"]
        cid = ctxs[0]["id"]
        check("contextos", [c["slug"] for c in ctxs] == ["ctx-contrato"], ctxs)
        erro = n.call("explorer.rows", {"contexto_id": cid, "table": "nao_existe"})
        check("erro com status 404", erro == {"id": erro["id"], "ok": False,
              "error": {"status": 404, "data": {"detail": "Tabela indisponível neste contexto."}}}, erro)
        desconhecido = n.call("nao.existe")
        check("método desconhecido", desconhecido["error"]["status"] == 404, desconhecido)
        stream = n.call("chat.stream", {"question": "x", "contexto_id": cid})
        check("chat sem chave → 503", stream["error"]["status"] == 503, stream)

        print("[3] Concorrência")
        ids = [n.request("explorer.rows", {"contexto_id": cid, "table": "vfact_orientacao_bolsa_resolved", "page": p})
               for p in (1, 2)]
        respostas = {}
        while len(respostas) < 2:
            msg = n.read()
            respostas[msg["id"]] = msg
        check("duas respostas, cada uma no seu id", sorted(respostas) == sorted(ids)
              and all(r["ok"] for r in respostas.values()))
        check("páginas certas", [respostas[i]["result"]["page"] for i in ids] == [1, 2])

        print("[4] Linha inválida e cancelamento")
        n.proc.stdin.write("isto não é json\n")
        n.proc.stdin.flush()
        check("segue respondendo após linha inválida", n.call("health")["ok"])
        rid = n.request("admin.system_status")
        n.send({"method": "$cancel", "params": {"id": rid}})
        msg = n.read()
        check("pedido cancelado ou já respondido", msg["id"] == rid and (msg["ok"] or msg["error"]["status"] == 499), msg)

        print("[5] Latência")
        lat = []
        for _ in range(30):
            t0 = time.monotonic()
            n.call("explorer.rows", {"contexto_id": cid, "table": "vfact_orientacao_bolsa_resolved", "search": "Projeto"})
            lat.append((time.monotonic() - t0) * 1000)
        print(f"       explorer.rows mediana {statistics.median(lat):.1f} ms")
        lat = []
        for _ in range(30):
            t0 = time.monotonic()
            n.call("me")
            lat.append((time.monotonic() - t0) * 1000)
        print(f"       me mediana {statistics.median(lat):.1f} ms")

        print("[6] Fim")
        n.proc.stdin.close()
        try:
            code = n.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            n.proc.kill()
            code = None
        resto = n.proc.stdout.read()
        check("sai quando o stdin fecha", code == 0, code)
        check("nada além do protocolo no stdout", resto == "", repr(resto[:200]))
        log = (data_dir / "nucleo.log").read_text(encoding="utf-8")
        check("logs foram para o stderr", "Núcleo pronto" in log)
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)

    print(f"\n{ok} OK, {len(falhas)} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
