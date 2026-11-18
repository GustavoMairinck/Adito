"""
Comandos de manutenção do Adito (substituem os do manage.py). Rodar de backend/nucleo:

    python -m core.cli load-context <pasta> [--index]
    python -m core.cli sync-embeddings --contexto <slug> [--table V] [--batch-size N] [--limit N] [--dry-run]
    python -m core.cli rebuild-embeddings --contexto <slug> [--table V] [--batch-size N] [--limit N] [--dry-run]
    python -m core.cli flush-data [--dry-run] [--keep-email EMAIL]

Usam o mesmo app.db do app (ORACULO_DATA_DIR / ORACULO_APP_DB) e o dados.duckdb atual.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

from analytics_index.config import TEXT_EMBEDDING_BATCH_SIZE

from . import db
from .records import Contexto, Tenant
from .schema import ensure_schema


class Erro(Exception):
    pass


def _embedder():
    from analytics_index.embedder import EmbedderIndisponivel, get_embedder

    try:
        return get_embedder()
    except EmbedderIndisponivel as exc:
        raise Erro(str(exc)) from exc


def _contexto(slug: str | None) -> Contexto:
    if not slug:
        raise Erro("Informe --contexto <slug>.")
    contexto = Contexto.first("slug = ? AND is_active = 1", [slug])
    if contexto is None:
        raise Erro(f"Contexto ativo '{slug}' não encontrado. Carregue com load-context.")
    return contexto


def load_context(args) -> None:
    from .contexts import index_contexto, load_context_dir

    nome = os.environ.get("DEFAULT_TENANT_NAME", "padrao")
    tenant = Tenant.first("name = ?", [nome], order="created_at") or Tenant(name=nome).insert()
    try:
        contexto, examples, errors = load_context_dir(args.pasta, tenant)
    except FileNotFoundError as exc:
        raise Erro(str(exc)) from exc
    if errors:
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        raise Erro(f"Contexto '{contexto.slug}' carregado como inativo: corrija os erros acima.")
    print(f"Contexto '{contexto.slug}' válido: {len(contexto.views)} view(s), {len(examples)} exemplo(s).")
    if args.index:
        summary = index_contexto(contexto, _embedder(), examples)
        print(f"Indexado: {summary['knowledge_items']} item(ns) de RAG, {summary['values']['created']} valor(es).")


def embeddings(args) -> None:
    from analytics_index.services import rebuild_text_embeddings, sync_text_embeddings

    contexto = _contexto(args.contexto)
    fn = rebuild_text_embeddings if args.comando == "rebuild-embeddings" else sync_text_embeddings
    try:
        summary = fn(
            contexto=contexto,
            embedder=None if args.dry_run else _embedder(),
            table=args.table,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            limit=args.limit,
        )
    except ValueError as exc:
        raise Erro(str(exc)) from exc
    for table, t in summary["tables"].items():
        print(f"{table}: found={t['found']} pending={t['pending']} created={t['created']} skipped={t['skipped']}")
    print(f"Concluído: created={summary['created']} skipped={summary['skipped']} dry_run={summary['dry_run']}")


def flush_data(args) -> None:
    """Apaga conversas, mensagens, auditoria de SQL e o estado do LangGraph (preserva contextos, RAG e widgets)."""
    from agents.config import CHECKPOINT_DB_PATH

    preservados = {r[0] for r in db.execute("SELECT id FROM core_user WHERE is_superuser = 1 OR username = 'local'")}
    if args.keep_email:
        preservados |= {r[0] for r in db.execute("SELECT id FROM core_user WHERE email = ?", [args.keep_email])}
    marcas = ", ".join("?" * len(preservados)) or "NULL"
    contagens = {
        "QueryExecution": db.execute("SELECT COUNT(*) FROM chat_queryexecution").fetchone()[0],
        "Message": db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0],
        "Conversation": db.execute("SELECT COUNT(*) FROM chat_conversation").fetchone()[0],
        "User": db.execute(f"SELECT COUNT(*) FROM core_user WHERE id NOT IN ({marcas})", list(preservados)).fetchone()[0],
    }
    for nome, total in contagens.items():
        print(f"  {nome}: {total}")
    if args.dry_run:
        print("DRY-RUN: nenhuma alteração foi feita.")
        return
    with db.transaction() as conn:
        conn.execute("DELETE FROM chat_queryexecution")
        conn.execute("DELETE FROM chat_message")
        conn.execute("DELETE FROM chat_conversation")
        apagar = f"(SELECT id FROM core_user WHERE id NOT IN ({marcas}))"
        conn.execute(f"DELETE FROM dashboard_widget WHERE dashboard_id IN (SELECT id FROM dashboard_dashboard WHERE user_id IN {apagar})", list(preservados))
        conn.execute(f"DELETE FROM dashboard_dashboard WHERE user_id IN {apagar}", list(preservados))
        conn.execute(f"DELETE FROM core_user WHERE id NOT IN ({marcas})", list(preservados))
    with sqlite3.connect(CHECKPOINT_DB_PATH) as conn:
        existentes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        removidos = sum(conn.execute(f"DELETE FROM {t}").rowcount for t in ("writes", "checkpoints") if t in existentes)
    print(f"Dados removidos. Checkpoints: {removidos} registro(s).")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m core.cli", description="Manutenção do Adito.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("load-context", help="Carrega e valida um contexto (views.json, rules.md, examples.json).")
    p.add_argument("pasta")
    p.add_argument("--index", action="store_true", help="Gera o RAG e o índice de valores (usa a chave do Gemini).")
    p.set_defaults(fn=load_context)

    for nome, ajuda in (("sync-embeddings", "Sincroniza os embeddings de valores."),
                        ("rebuild-embeddings", "Recria os embeddings de valores.")):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument("--contexto")
        p.add_argument("--table")
        p.add_argument("--batch-size", type=int, default=TEXT_EMBEDDING_BATCH_SIZE)
        p.add_argument("--limit", type=int)
        p.add_argument("--dry-run", action="store_true")
        p.set_defaults(fn=embeddings)

    p = sub.add_parser("flush-data", help="Apaga conversas e auditoria de SQL.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--keep-email")
    p.set_defaults(fn=flush_data)

    args = parser.parse_args(argv)
    ensure_schema()
    try:
        args.fn(args)
    except Erro as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

