"""
Versão do esquema do app.db (PRAGMA user_version), sem o sistema de migrations do Django.

- Banco novo: cria as tabelas de schema.sql.
- Banco criado pelo Django (instalações anteriores): adota as tabelas como estão.
- Mudanças futuras: acrescentar uma função em MIGRACOES; antes de aplicar, o app.db é
  copiado para app.db.bak-v<versão> pela API de backup do SQLite.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import db
from .datastore import app_db_path

SCHEMA_SQL = Path(__file__).with_name("schema.sql")

# Versão 1 = esquema herdado do Django. Cada item leva o banco da versão i+1 para i+2.
MIGRACOES: list = []
VERSAO = 1 + len(MIGRACOES)


def _backup(versao: int) -> Path:
    destino = Path(str(app_db_path()) + f".bak-v{versao}")
    with sqlite3.connect(destino) as copia:
        db.connect().backup(copia)
    return destino


def _pendencias_do_django(conn: sqlite3.Connection) -> None:
    """Migration de dados do Django que um banco antigo talvez não tenha rodado.

    knowledge.0002: os vetores da Mistral não servem no espaço do Gemini; zera para reindexar.
    """
    tem_django = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'django_migrations'"
    ).fetchone()
    if not tem_django:
        return
    aplicada = conn.execute(
        "SELECT 1 FROM django_migrations WHERE app = 'knowledge' AND name = '0002_reset_embeddings_for_gemini'"
    ).fetchone()
    if not aplicada:
        with db.transaction():
            conn.execute("UPDATE knowledge_knowledgeitem SET embedding = NULL")
            conn.execute("DELETE FROM analytics_text_embedding")


def ensure_schema() -> int:
    """Deixa o app.db na versão atual. Rápido quando já está em dia (só lê o user_version)."""
    conn = db.connect()
    versao = conn.execute("PRAGMA user_version").fetchone()[0]
    if versao == VERSAO:
        return versao
    if versao == 0:
        # Novo ou herdado do Django: IF NOT EXISTS cria só o que falta.
        conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        _pendencias_do_django(conn)
        conn.execute("PRAGMA user_version = 1")
        versao = 1
    if versao < VERSAO:
        _backup(versao)
        for migracao in MIGRACOES[versao - 1:]:
            with db.transaction():
                migracao(conn)
                versao += 1
                conn.execute(f"PRAGMA user_version = {versao}")
    return versao
