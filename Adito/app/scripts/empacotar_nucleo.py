#!/usr/bin/env python3
"""Empacota o núcleo Python (`adito-backend`) para ir dentro do instalador (US-011).

1. roda o PyInstaller com `backend/adito-backend.spec` (executável único, sem Python na máquina do usuário);
2. confere que ele sobe e responde pelo protocolo stdin/stdout (evento `ready`);
3. copia para `src-tauri/binaries/adito-backend-<alvo-rust>[.exe]`, o nome que o Tauri exige no `externalBin`.

Uso (a partir de Adito/app, com o .venv do app e o pyinstaller instalados):
    .venv/bin/python scripts/empacotar_nucleo.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
BACKEND = APP / "backend"
BINARIOS = APP / "src-tauri" / "binaries"
EXE = ".exe" if os.name == "nt" else ""


def alvo_rust() -> str:
    """Triplo do alvo (ex.: x86_64-unknown-linux-gnu), que o Tauri usa no nome do sidecar."""
    saida = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
    for linha in saida.splitlines():
        if linha.startswith("host:"):
            return linha.split(":", 1)[1].strip()
    raise SystemExit("não achei o alvo em `rustc -vV`")


def conferir(binario: Path) -> dict:
    """Sobe o núcleo empacotado numa pasta vazia e espera o `ready`."""
    with tempfile.TemporaryDirectory(prefix="adito-nucleo-") as pasta:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("ADITO_", "GEMINI", "PYTHON", "VIRTUAL_ENV"))}
        env["ADITO_DATA_DIR"] = pasta
        proc = subprocess.Popen(
            [str(binario)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True
        )
        try:
            linha = proc.stdout.readline()
        finally:
            proc.stdin.close()
            proc.wait(timeout=30)
        try:
            msg = json.loads(linha)
        except ValueError:
            raise SystemExit(f"o núcleo empacotado não respondeu:\n{proc.stderr.read()[-3000:]}")
        if msg.get("event") != "ready":
            raise SystemExit(f"o núcleo empacotado falhou ao subir: {msg}\n{proc.stderr.read()[-3000:]}")
        return msg["data"]


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(BACKEND / "adito-backend.spec"), "--noconfirm",
         "--distpath", str(BACKEND / "dist"), "--workpath", str(BACKEND / "build")],
        check=True, cwd=APP,
    )
    binario = BACKEND / "dist" / f"adito-backend{EXE}"
    info = conferir(binario)
    print(f"núcleo ok: {info['methods']} métodos, schema {info['schema']}, subiu em {info['startup_ms']} ms")

    BINARIOS.mkdir(parents=True, exist_ok=True)
    destino = BINARIOS / f"adito-backend-{alvo_rust()}{EXE}"
    shutil.copy2(binario, destino)
    print(f"copiado para {destino.relative_to(APP)} ({destino.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
