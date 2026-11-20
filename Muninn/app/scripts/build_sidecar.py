"""
Gera o sidecar `muninn-backend` com PyInstaller e o copia para src-tauri/binaries com o nome
que o Tauri espera (`muninn-backend-<target-triple>[.exe]`).

Uso (com o .venv do app ativo e `pip install pyinstaller`):
    python Muninn/app/scripts/build_sidecar.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
BACKEND = APP / "backend"


def target_triple() -> str:
    out = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
    return next(l.split(": ", 1)[1] for l in out.splitlines() if l.startswith("host: "))


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "muninn-backend.spec"],
        cwd=BACKEND,
        check=True,
    )
    ext = ".exe" if sys.platform == "win32" else ""
    origem = BACKEND / "dist" / f"muninn-backend{ext}"
    destino_dir = APP / "src-tauri" / "binaries"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"muninn-backend-{target_triple()}{ext}"
    shutil.copy2(origem, destino)
    print(f"sidecar pronto: {destino}")


if __name__ == "__main__":
    main()
