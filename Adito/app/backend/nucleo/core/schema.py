"""
Versão do esquema do app.db (PRAGMA user_version).

- Banco novo: cria as tabelas de schema.sql já na versão atual.
- Banco antigo (criado pela versão com Django, versão 0): adota as tabelas e migra até a atual.
- Mudança de esquema: acrescentar uma função em MIGRACOES. Antes de aplicar, o app.db é copiado
  para app.db.bak-v<versão> pela API de backup do SQLite.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from . import db
from .datastore import app_db_path

SCHEMA_SQL = Path(__file__).with_name("schema.sql")

# Tabelas que só o Django usava (autenticação, admin, sessões, controle de migrations).
TABELAS_DJANGO = (
    "django_admin_log", "django_session", "django_content_type", "django_migrations",
    "auth_group_permissions", "auth_permission", "auth_group",
    "core_user_groups", "core_user_user_permissions",
)
# Contextos que saíram do produto: a demonstração de vendas herdada do Oráculo-ESX.
CONTEXTOS_REMOVIDOS = ("exemplo-vendas",)

_CORE_USER_V2 = (
    'CREATE TABLE "core_user_v2" ("id" char(32) NOT NULL PRIMARY KEY, "username" varchar(150) NOT NULL UNIQUE, '
    '"first_name" varchar(150) NOT NULL, "last_name" varchar(150) NOT NULL, "email" varchar(254) NOT NULL, '
    '"is_staff" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, '
    '"tenant_id" char(32) NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED)'
)
_COLUNAS_USER_V2 = "id, username, first_name, last_name, email, is_staff, created_at, updated_at, tenant_id"


def _ids_dos_contextos_removidos(conn: sqlite3.Connection) -> list[str]:
    marcas = ", ".join("?" * len(CONTEXTOS_REMOVIDOS))
    return [r[0] for r in conn.execute(f"SELECT id FROM core_contexto WHERE slug IN ({marcas})", CONTEXTOS_REMOVIDOS)]


def _apagar_contextos_removidos(conn: sqlite3.Connection) -> None:
    """Apaga os contextos removidos e o que depende deles: conversas, histórico, widgets, auditoria e RAG."""
    ids = _ids_dos_contextos_removidos(conn)
    if not ids:
        return
    m = ", ".join("?" * len(ids))
    conversas = [r[0] for r in conn.execute(f"SELECT id FROM chat_conversation WHERE contexto_id IN ({m})", ids)]
    if conversas:
        c = ", ".join("?" * len(conversas))
        conn.execute(
            f"DELETE FROM chat_queryexecution WHERE message_id IN "
            f"(SELECT id FROM chat_message WHERE conversation_id IN ({c}))", conversas,
        )
        conn.execute(f"DELETE FROM chat_message WHERE conversation_id IN ({c})", conversas)
        conn.execute(f"DELETE FROM chat_conversation WHERE id IN ({c})", conversas)
        # Estado do LangGraph dessas conversas (thread_id termina em ":conv_<id com hífens>").
        existentes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        for conv in conversas:
            fio = f"%:conv_{db.from_db_id(conv)}"
            for tabela in ("writes", "checkpoints"):
                if tabela in existentes:
                    conn.execute(f"DELETE FROM {tabela} WHERE thread_id LIKE ?", [fio])
    for tabela in ("chat_queryexecution", "dashboard_widget", "knowledge_knowledgeitem", "analytics_text_embedding"):
        conn.execute(f"DELETE FROM {tabela} WHERE contexto_id IN ({m})", ids)
    conn.execute(f"DELETE FROM core_contexto WHERE id IN ({m})", ids)


def _v2_sem_django_e_sem_vendas(conn: sqlite3.Connection) -> None:
    """Versão 1 → 2: tira o que sobrou do Django e a demonstração de vendas."""
    _apagar_contextos_removidos(conn)
    for tabela in TABELAS_DJANGO:
        conn.execute(f'DROP TABLE IF EXISTS "{tabela}"')
    colunas = {r[1] for r in conn.execute("PRAGMA table_info(core_user)")}
    if "password" in colunas:
        # core_user sem as colunas de autenticação do Django (o app não tem login).
        conn.execute(_CORE_USER_V2)
        conn.execute(f"INSERT INTO core_user_v2 ({_COLUNAS_USER_V2}) SELECT {_COLUNAS_USER_V2} FROM core_user")
        conn.execute("DROP TABLE core_user")
        conn.execute('ALTER TABLE "core_user_v2" RENAME TO "core_user"')
        conn.execute('CREATE INDEX IF NOT EXISTS "core_user_tenant_id_8a6e30cc" ON "core_user" ("tenant_id")')


def _v3_embedding_metadata_em_analytics(conn: sqlite3.Connection) -> None:
    """Versão 2 → 3: guarda provedor e modelo dos vetores em analytics_text_embedding."""
    colunas = {r[1] for r in conn.execute("PRAGMA table_info(analytics_text_embedding)")}
    if "embedding_provider" not in colunas:
        conn.execute('ALTER TABLE "analytics_text_embedding" ADD COLUMN "embedding_provider" varchar(50) NULL')
    if "embedding_model" not in colunas:
        conn.execute('ALTER TABLE "analytics_text_embedding" ADD COLUMN "embedding_model" varchar(120) NULL')


def _v4_conversa_fixada(conn: sqlite3.Connection) -> None:
    """Versão 3 → 4: adiciona coluna is_pinned em chat_conversation para fixar conversas."""
    colunas = {r[1] for r in conn.execute("PRAGMA table_info(chat_conversation)")}
    if "is_pinned" not in colunas:
        conn.execute('ALTER TABLE "chat_conversation" ADD COLUMN "is_pinned" bool NOT NULL DEFAULT 0')


# Versão 1 = esquema herdado do Django. Cada item leva o banco da versão i+1 para i+2.
MIGRACOES: list = [_v2_sem_django_e_sem_vendas, _v3_embedding_metadata_em_analytics, _v4_conversa_fixada]
VERSAO = 1 + len(MIGRACOES)


def _backup(versao: int) -> Path:
    destino = Path(str(app_db_path()) + f".bak-v{versao}")
    # closing(): o "with" do sqlite3 só controla a transação; sem fechar, o arquivo fica preso no Windows.
    with closing(sqlite3.connect(destino)) as copia:
        db.connect().backup(copia)
    return destino


def _pendencias_do_django(conn: sqlite3.Connection) -> None:
    """Banco da versão com Django: aplica a migration de dados que ele talvez não tenha rodado.

    Precisa olhar a tabela django_migrations para saber; a versão 2 apaga essa tabela depois.

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
        novo = not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'core_tenant'").fetchone()
        # IF NOT EXISTS: num banco antigo cria só o que falta; num banco novo cria tudo.
        conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        if novo:
            conn.execute(f"PRAGMA user_version = {VERSAO}")
            return VERSAO
        _pendencias_do_django(conn)
        conn.execute("PRAGMA user_version = 1")
        versao = 1
    if versao < VERSAO:
        _backup(versao)
        # Refazer tabela (core_user) exige as chaves estrangeiras desligadas; elas são conferidas
        # antes de gravar, e qualquer problema desfaz a migração inteira.
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            for migracao in MIGRACOES[versao - 1:]:
                with db.transaction():
                    migracao(conn)
                    problemas = conn.execute("PRAGMA foreign_key_check").fetchall()
                    if problemas:
                        raise RuntimeError(f"Migração para a versão {versao + 1} quebraria chaves estrangeiras: {problemas[:5]}")
                    versao += 1
                    conn.execute(f"PRAGMA user_version = {versao}")
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
    return versao
