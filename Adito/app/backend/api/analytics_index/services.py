import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from core import db
from core.datastore import connect_dados
from core.db import to_db_id
from core.records import AnalyticsTextEmbedding
from core.vectors import nearest

from .config import TEXT_EMBEDDING_BATCH_SIZE, TEXT_EMBEDDING_TOP_K


@dataclass(frozen=True)
class TextEmbeddingCandidate:
    source_table: str
    embedding_text: str
    payload_json: dict
    value_hash: str


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def value_hash(source_table: str, embedding_text: str) -> str:
    raw = f"{source_table}\n{embedding_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_table_config(contexto, source_table: str) -> dict:
    """Campos embedados de uma view vêm do embed_columns do views.json (nunca colunas sensíveis)."""
    view = contexto.view_config(source_table)
    fields = list(view.get("embed_columns", [])) if view else []
    if not fields:
        configured = ", ".join(configured_tables(contexto)) or "nenhuma"
        raise ValueError(f"View sem embed_columns no contexto '{contexto.slug}': {source_table}. Configuradas: {configured}")
    return {"fields": fields, "labels": {field: field.replace("_", " ").capitalize() for field in fields}}


def configured_tables(contexto, table: str | None = None) -> list[str]:
    tables = [view["name"] for view in contexto.views if view.get("embed_columns")]
    if table:
        get_table_config(contexto, table)
        return [table]
    return tables


def make_embedding_text(config: dict, payload: dict) -> str:
    labels = config.get("labels", {})
    lines = []

    for field in config["fields"]:
        value = normalize_text(payload.get(field))
        if not value:
            continue
        label = labels.get(field, field)
        lines.append(f"{label}: {value}")

    return "\n".join(lines)


def make_candidate(source_table: str, config: dict, payload: dict) -> TextEmbeddingCandidate | None:
    cleaned_payload = {field: normalize_text(payload.get(field)) for field in config["fields"]}
    embedding_text = make_embedding_text(config, cleaned_payload)
    if not embedding_text:
        return None

    return TextEmbeddingCandidate(
        source_table=source_table,
        embedding_text=embedding_text,
        payload_json=cleaned_payload,
        value_hash=value_hash(source_table, embedding_text),
    )


def _quote_name(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def fetch_distinct_candidates(contexto, source_table: str) -> list[TextEmbeddingCandidate]:
    config = get_table_config(contexto, source_table)
    fields = config["fields"]
    quoted_fields = ", ".join(_quote_name(field) for field in fields)
    non_empty_checks = [
        f"({_quote_name(field)} IS NOT NULL AND TRIM(CAST({_quote_name(field)} AS TEXT)) <> '')"
        for field in fields
    ]
    where = " OR ".join(non_empty_checks)

    with connect_dados() as conn:
        found = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE LOWER(table_name) = LOWER(?)",
            [source_table],
        ).fetchone()
        if found is None:
            raise ValueError(
                f"Tabela/view analítica '{source_table}' não encontrada no dados.duckdb. "
                "Carregue os dados antes de sincronizar embeddings."
            )
        rows = conn.execute(f"SELECT DISTINCT {quoted_fields} FROM {_quote_name(source_table)} WHERE {where}").fetchall()

    candidates = []
    for row in rows:
        payload = dict(zip(fields, tuple(row)))
        candidate = make_candidate(source_table, config, payload)
        if candidate:
            candidates.append(candidate)
    return candidates


def iter_batches(items: list, batch_size: int) -> Iterable[list]:
    if batch_size < 1:
        raise ValueError("batch_size deve ser maior que zero.")
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def embed_texts(embedder, texts: list[str]) -> list:
    embeddings = embedder.embed_documents(texts)
    if len(embeddings) == len(texts):
        return embeddings
    return [embedder.embed_query(text) for text in texts]


def _existing_hashes(contexto, source_table: str, hashes: list[str]) -> set[str]:
    found: set[str] = set()
    for start in range(0, len(hashes), 500):  # limite de parâmetros do SQLite
        chunk = hashes[start:start + 500]
        found.update(row[0] for row in db.execute(
            "SELECT value_hash FROM analytics_text_embedding WHERE contexto_id = ? AND source_table = ? "
            f"AND value_hash IN ({', '.join('?' * len(chunk))})",
            [to_db_id(contexto.id), source_table, *chunk],
        ))
    return found


def _insert_ignore(rows: list[AnalyticsTextEmbedding]) -> None:
    """bulk_create(ignore_conflicts=True): a constraint única descarta valores repetidos."""
    if not rows:
        return
    now = db.utcnow()
    names = AnalyticsTextEmbedding.columns()
    for row in rows:
        row.created_at = row.updated_at = now
    with db.transaction() as conn:
        conn.executemany(
            f"INSERT OR IGNORE INTO analytics_text_embedding ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})",
            [[AnalyticsTextEmbedding.db_value(n, getattr(row, n)) for n in names] for row in rows],
        )


def sync_text_embeddings(
    contexto,
    embedder,
    table: str | None = None,
    batch_size: int = TEXT_EMBEDDING_BATCH_SIZE,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    summary = {"tables": {}, "created": 0, "skipped": 0, "dry_run": dry_run}

    for source_table in configured_tables(contexto, table):
        candidates = fetch_distinct_candidates(contexto, source_table)
        if limit is not None:
            candidates = candidates[:limit]
        hashes = [candidate.value_hash for candidate in candidates]
        existing_hashes = _existing_hashes(contexto, source_table, hashes)
        missing = [candidate for candidate in candidates if candidate.value_hash not in existing_hashes]

        summary["tables"][source_table] = {
            "found": len(candidates),
            "pending": len(missing),
            "created": 0,
            "skipped": len(candidates) - len(missing),
        }
        summary["skipped"] += len(candidates) - len(missing)

        if dry_run or not missing:
            continue

        for batch in iter_batches(missing, batch_size):
            texts = [candidate.embedding_text for candidate in batch]
            embeddings = embed_texts(embedder, texts)
            rows = [
                AnalyticsTextEmbedding(
                    id=db.new_id(),
                    tenant_id=contexto.tenant_id,
                    contexto_id=contexto.id,
                    source_table=candidate.source_table,
                    embedding_text=candidate.embedding_text,
                    payload_json=candidate.payload_json,
                    value_hash=candidate.value_hash,
                    embedding=embedding,
                )
                for candidate, embedding in zip(batch, embeddings)
            ]
            _insert_ignore(rows)
            summary["tables"][source_table]["created"] += len(rows)
            summary["created"] += len(rows)

    return summary


def rebuild_text_embeddings(
    contexto,
    embedder,
    table: str | None = None,
    batch_size: int = TEXT_EMBEDDING_BATCH_SIZE,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    tables = configured_tables(contexto, table)
    if dry_run:
        return sync_text_embeddings(contexto, embedder, table=table, batch_size=batch_size, dry_run=True, limit=limit)

    with db.transaction():
        if table:
            db.execute(
                f"DELETE FROM analytics_text_embedding WHERE contexto_id = ? AND source_table IN ({', '.join('?' * len(tables))})",
                [to_db_id(contexto.id), *tables],
            )
        else:
            db.execute("DELETE FROM analytics_text_embedding WHERE contexto_id = ?", [to_db_id(contexto.id)])

    return sync_text_embeddings(contexto, embedder, table=table, batch_size=batch_size, dry_run=False, limit=limit)


def search_text_embeddings(contexto, query_embedding, table: str | None = None, top_k: int = TEXT_EMBEDDING_TOP_K) -> list[dict]:
    where, params = "contexto_id = ? AND embedding IS NOT NULL", [to_db_id(contexto.id)]
    if table:
        where, params = where + " AND source_table = ?", [*params, table]
    qs = AnalyticsTextEmbedding.select(where, params)

    return [
        {
            "source_table": row.source_table,
            "embedding_text": row.embedding_text,
            "payload_json": row.payload_json,
            "distance": distance,
        }
        for row, distance in nearest(qs, query_embedding, top_k)
    ]
