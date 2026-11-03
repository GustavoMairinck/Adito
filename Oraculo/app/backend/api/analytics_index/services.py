import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from django.db import transaction

from core.datastore import connect_dados
from core.vectors import nearest

from .config import TEXT_EMBEDDING_BATCH_SIZE, TEXT_EMBEDDING_TABLES, TEXT_EMBEDDING_TOP_K
from .models import AnalyticsTextEmbedding


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


def get_table_config(source_table: str) -> dict:
    try:
        return TEXT_EMBEDDING_TABLES[source_table]
    except KeyError as exc:
        configured = ", ".join(sorted(TEXT_EMBEDDING_TABLES))
        raise ValueError(f"Tabela sem configuração de embeddings: {source_table}. Configuradas: {configured}") from exc


def configured_tables(table: str | None = None) -> list[str]:
    if table:
        get_table_config(table)
        return [table]
    return list(TEXT_EMBEDDING_TABLES.keys())


def make_embedding_text(source_table: str, payload: dict) -> str:
    config = get_table_config(source_table)
    labels = config.get("labels", {})
    lines = []

    for field in config["fields"]:
        value = normalize_text(payload.get(field))
        if not value:
            continue
        label = labels.get(field, field)
        lines.append(f"{label}: {value}")

    return "\n".join(lines)


def make_candidate(source_table: str, payload: dict) -> TextEmbeddingCandidate | None:
    cleaned_payload = {field: normalize_text(payload.get(field)) for field in get_table_config(source_table)["fields"]}
    embedding_text = make_embedding_text(source_table, cleaned_payload)
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


def fetch_distinct_candidates(tenant, source_table: str) -> list[TextEmbeddingCandidate]:
    config = get_table_config(source_table)
    fields = config["fields"]
    quoted_fields = ", ".join(_quote_name(field) for field in fields)
    non_empty_checks = [
        f"({_quote_name(field)} IS NOT NULL AND TRIM(CAST({_quote_name(field)} AS TEXT)) <> '')"
        for field in fields
    ]
    where = " OR ".join(non_empty_checks)

    with connect_dados() as conn:
        found = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')",
            [source_table],
        ).fetchone()
        if found is None:
            raise ValueError(
                f"Tabela/view analítica '{source_table}' não encontrada no dados.db. "
                "Carregue os dados antes de sincronizar embeddings."
            )
        rows = conn.execute(f"SELECT DISTINCT {quoted_fields} FROM {_quote_name(source_table)} WHERE {where}").fetchall()

    candidates = []
    for row in rows:
        payload = dict(zip(fields, tuple(row)))
        candidate = make_candidate(source_table, payload)
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


def sync_text_embeddings(
    tenant,
    embedder,
    table: str | None = None,
    batch_size: int = TEXT_EMBEDDING_BATCH_SIZE,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    summary = {"tables": {}, "created": 0, "skipped": 0, "dry_run": dry_run}

    for source_table in configured_tables(table):
        candidates = fetch_distinct_candidates(tenant, source_table)
        if limit is not None:
            candidates = candidates[:limit]
        hashes = [candidate.value_hash for candidate in candidates]
        existing_hashes = set(
            AnalyticsTextEmbedding.objects.filter(
                tenant=tenant,
                source_table=source_table,
                value_hash__in=hashes,
            ).values_list("value_hash", flat=True)
        )
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
                    tenant=tenant,
                    source_table=candidate.source_table,
                    embedding_text=candidate.embedding_text,
                    payload_json=candidate.payload_json,
                    value_hash=candidate.value_hash,
                    embedding=embedding,
                )
                for candidate, embedding in zip(batch, embeddings)
            ]
            AnalyticsTextEmbedding.objects.bulk_create(rows, ignore_conflicts=True)
            summary["tables"][source_table]["created"] += len(rows)
            summary["created"] += len(rows)

    return summary


def rebuild_text_embeddings(
    tenant,
    embedder,
    table: str | None = None,
    batch_size: int = TEXT_EMBEDDING_BATCH_SIZE,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    tables = configured_tables(table)
    if dry_run:
        return sync_text_embeddings(tenant, embedder, table=table, batch_size=batch_size, dry_run=True, limit=limit)

    with transaction.atomic():
        AnalyticsTextEmbedding.objects.filter(tenant=tenant, source_table__in=tables).delete()

    return sync_text_embeddings(tenant, embedder, table=table, batch_size=batch_size, dry_run=False, limit=limit)


def search_text_embeddings(tenant, query_embedding, table: str | None = None, top_k: int = TEXT_EMBEDDING_TOP_K) -> list[dict]:
    qs = AnalyticsTextEmbedding.objects.filter(tenant=tenant, embedding__isnull=False)
    if table:
        qs = qs.filter(source_table=table)

    return [
        {
            "source_table": row.source_table,
            "embedding_text": row.embedding_text,
            "payload_json": row.payload_json,
            "distance": distance,
        }
        for row, distance in nearest(qs, query_embedding, top_k)
    ]
