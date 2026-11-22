# -*- mode: python ; coding: utf-8 -*-
# Empacota o núcleo Python do Adito num executável único, `adito-backend` (US-011).
#
# O Tauri sobe esse executável ao lado do app (externalBin) e conversa com ele por
# stdin/stdout. Não precisa de Python instalado na máquina do usuário.
#
#   cd Adito/app && .venv/bin/pyinstaller backend/adito-backend.spec --noconfirm
#
# Saída: Adito/app/backend/dist/adito-backend(.exe). O script
# Adito/app/scripts/empacotar_nucleo.py roda o build e copia o binário para src-tauri/binaries/
# com o sufixo da plataforma que o Tauri exige.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

BACKEND = Path(SPECPATH)
NUCLEO = BACKEND / "nucleo"
APP = BACKEND.parent

# Módulos do próprio núcleo: alguns entram por import tardio (dentro de funções).
proprios = []
for pacote in ("agents", "analytics_index", "core", "rpc"):
    proprios += collect_submodules(pacote, filter=lambda nome: ".tests" not in nome and not nome.endswith(".tests"))

# Bibliotecas que carregam partes por import dinâmico.
externos = (
    collect_submodules("langchain_google_genai")
    + collect_submodules("langgraph")
    + collect_submodules("langgraph.checkpoint.sqlite")
    + collect_submodules("langfuse")
    + collect_submodules("sqlglot.dialects")
    + collect_submodules("tiktoken_ext")
)

dados = [
    # schema do app.db, lido ao lado de core/schema.py
    (str(NUCLEO / "core" / "schema.sql"), "core"),
    # contextos padrão (views, regras e exemplos do agente); REPO_APP_DIR aponta para cá empacotado
    (str(APP / "contexts"), "contexts"),
]
for pacote in ("langchain_core", "langchain_google_genai", "langgraph", "google.genai", "certifi"):
    try:
        dados += collect_data_files(pacote)
    except Exception:
        pass

a = Analysis(
    [str(NUCLEO / "desktop_server.py")],
    pathex=[str(NUCLEO)],
    binaries=[],
    datas=dados,
    hiddenimports=proprios + externos,
    excludes=[
        # Nada disso roda no núcleo desktop (sem servidor HTTP, sem notebooks, sem testes).
        "tkinter", "matplotlib", "IPython", "jupyter", "notebook", "pytest",
        "django", "daphne", "uvicorn", "fastapi",
        "langchain_community",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="adito-backend",
    debug=False,
    strip=False,
    upx=False,
    # Aplicativo de console: o protocolo é stdin/stdout. O Tauri esconde a janela no Windows
    # (CREATE_NO_WINDOW em src-tauri/src/lib.rs).
    console=True,
)
