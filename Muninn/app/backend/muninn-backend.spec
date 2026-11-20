# -*- mode: python ; coding: utf-8 -*-
# Empacota o núcleo Python (nucleo/desktop_server.py) num executável único, o sidecar
# `muninn-backend` que o Tauri sobe. Gerado por scripts/build_sidecar.py; rode a partir de Muninn/app/backend.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hidden = []
for pkg in ("rpc", "core", "agents", "analytics_index", "langgraph", "langchain_google_genai", "sqlglot"):
    hidden += collect_submodules(pkg)

datas = [
    ("nucleo/core/schema.sql", "core"),
    ("../contexts", "contexts"),
]
datas += collect_data_files("langchain_core")

a = Analysis(
    ["nucleo/desktop_server.py"],
    pathex=["nucleo"],
    hiddenimports=hidden,
    datas=datas,
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="muninn-backend",
    console=True,  # o Tauri fala com ele por stdin/stdout; a janela é escondida pelo CREATE_NO_WINDOW
    upx=False,
)
