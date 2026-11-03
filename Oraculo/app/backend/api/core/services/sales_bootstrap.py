import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.db import connection, transaction
from langchain_mistralai import MistralAIEmbeddings

from agents.config import MISTRAL_API_KEY, MISTRAL_EMBEDDING_MODEL
from analytics_index.services import sync_text_embeddings
from core.models import Tenant
from knowledge.models import KnowledgeItem


ROOT_DIR = Path(__file__).resolve().parents[4]


def _resolve_sales_dir() -> Path:
    candidates = [
        os.getenv("SALES_BOOTSTRAP_DIR"),
        Path.cwd() / "mudanças" / "mudanca",
        ROOT_DIR / "mudanças" / "mudanca",
        Path(__file__).resolve().parents[3] / "mudanças" / "mudanca",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if (path / "schema-ddl.sql").exists():
            return path
    checked = ", ".join(str(Path(candidate)) for candidate in candidates if candidate)
    raise FileNotFoundError(f"Pasta de bootstrap de vendas não encontrada. Caminhos verificados: {checked}")


SALES_DIR = _resolve_sales_dir()
SALES_VIEW = "vfactvendasresolved"
SALES_TABLES = [
    "fact_vendas",
    "dim_tempo",
    "dim_produto",
    "dim_cliente",
    "dim_regiao",
    "dim_canal",
    "dim_vendedor",
]


@dataclass
class SalesBootstrapOptions:
    tenant: Tenant
    reset: bool = False
    dry_run: bool = False
    run_training: bool = True
    run_embeddings: bool = True


def _quote_name(name: str) -> str:
    return connection.ops.quote_name(name)


def _set_search_path(cursor, schema_name: str):
    cursor.execute(f"SET search_path TO {_quote_name(schema_name)}, public")


def _split_sql(sql: str) -> list[str]:
    parts = []
    current = []
    in_single_quote = False
    previous = ""

    for char in sql:
        if char == "'" and previous != "\\":
            in_single_quote = not in_single_quote
        if char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                parts.append(statement)
            current = []
        else:
            current.append(char)
        previous = char

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _clean_sqlserver_lines(sql: str) -> str:
    cleaned = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("--"):
            continue
        if stripped.upper() == "GO":
            continue
        if re.match(r"^USE\s+\[[^\]]+\]\s*;?$", stripped, flags=re.IGNORECASE):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _load_schema_sql() -> str:
    return (SALES_DIR / "schema-ddl.sql").read_text(encoding="utf-8")


def _load_insert_statements() -> list[str]:
    files = ["03-dimensoes-faltantes.sql", "02-schema-dados.sql"]
    statements = []
    for fname in files:
        path = SALES_DIR / fname
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        cleaned = _clean_sqlserver_lines(raw)
        statements.extend(
            s for s in _split_sql(cleaned)
            if s.lstrip().upper().startswith("INSERT INTO ")
        )
    return statements


def _get_embedder():
    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY não configurada; não é possível treinar knowledge/embeddings.")
    return MistralAIEmbeddings(model=MISTRAL_EMBEDDING_MODEL, api_key=MISTRAL_API_KEY)


def _reset_sales_objects(cursor, schema_name: str):
    _set_search_path(cursor, schema_name)
    cursor.execute(f"DROP VIEW IF EXISTS {_quote_name(SALES_VIEW)} CASCADE")
    for table in SALES_TABLES:
        cursor.execute(f"DROP TABLE IF EXISTS {_quote_name(table)} CASCADE")


def _apply_schema(cursor, schema_name: str) -> int:
    _set_search_path(cursor, schema_name)
    statements = _split_sql(_load_schema_sql())
    for statement in statements:
        cursor.execute(statement)
    return len(statements)


def _apply_data(cursor, schema_name: str) -> dict[str, int]:
    _set_search_path(cursor, schema_name)
    counts = {table: 0 for table in SALES_TABLES}
    for statement in _load_insert_statements():
        cursor.execute(statement)
        match = re.match(r"INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", statement, flags=re.IGNORECASE)
        if match:
            table = match.group(1).lower()
            counts[table] = counts.get(table, 0) + 1
    return counts


def _count_rows(cursor, schema_name: str) -> dict[str, int]:
    _set_search_path(cursor, schema_name)
    counts = {}
    for table in SALES_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM {_quote_name(table)}")
        counts[table] = int(cursor.fetchone()[0])
    cursor.execute(f"SELECT COUNT(*) FROM {_quote_name(SALES_VIEW)}")
    counts[SALES_VIEW] = int(cursor.fetchone()[0])
    return counts


def _train_sales_knowledge(tenant: Tenant, embedder) -> dict[str, int]:
    KnowledgeItem.objects.filter(tenant=tenant, item_type__in=["query_example", "ddl", "doc"]).delete()
    counts = {"query_example": 0, "ddl": 0, "doc": 0}

    examples = json.loads((SALES_DIR / "exemples.json").read_text(encoding="utf-8"))
    for example in examples:
        question = (example.get("question") or "").strip()
        sql = (example.get("sql") or "").strip()
        if not question or not sql:
            continue
        KnowledgeItem.objects.create(
            tenant=tenant,
            item_type="query_example",
            content=f"Q: {question}\nSQL: {sql}",
            metadata={"question": question, "sql": sql, "source": "mudanças/mudanca/exemples.json"},
            embedding=embedder.embed_query(question),
        )
        counts["query_example"] += 1

    ddl = (SALES_DIR / "schema-ddl.sql").read_text(encoding="utf-8").strip()
    KnowledgeItem.objects.create(
        tenant=tenant,
        item_type="ddl",
        content=ddl,
        metadata={"source": "mudanças/mudanca/schema-ddl.sql"},
        embedding=embedder.embed_query(ddl),
    )
    counts["ddl"] += 1

    doc = (SALES_DIR / "entity-filter-rules.md").read_text(encoding="utf-8").strip()
    KnowledgeItem.objects.create(
        tenant=tenant,
        item_type="doc",
        content=doc,
        metadata={"source": "mudanças/mudanca/entity-filter-rules.md"},
        embedding=embedder.embed_query(doc),
    )
    counts["doc"] += 1

    return counts


def resolve_tenant(tenant_arg: str | None = None, tenant_schema: str | None = None) -> Tenant:
    if tenant_schema:
        tenant, _ = Tenant.objects.get_or_create(
            db_schema_name=tenant_schema,
            defaults={"name": tenant_schema, "is_active": True},
        )
        return tenant

    if not tenant_arg:
        tenant_arg = os.getenv("DEFAULT_TENANT_NAME") or os.getenv("DEFAULT_TENANT_SCHEMA") or "fapes"

    filters: dict[str, Any] = {"name__iexact": tenant_arg}
    try:
        filters = {"id": uuid.UUID(str(tenant_arg))}
    except ValueError:
        pass

    tenant = Tenant.objects.filter(**filters).first()
    if tenant:
        return tenant

    tenant, _ = Tenant.objects.get_or_create(
        db_schema_name=tenant_arg,
        defaults={"name": tenant_arg, "is_active": True},
    )
    return tenant


def run_sales_bootstrap(options: SalesBootstrapOptions) -> dict:
    tenant = options.tenant
    schema_name = tenant.db_schema_name or tenant.name
    if not schema_name:
        raise ValueError("Tenant sem db_schema_name ou name configurado.")

    summary = {
        "tenant": {"id": str(tenant.id), "name": tenant.name, "schema": schema_name},
        "dry_run": options.dry_run,
        "reset": options.reset,
        "schema": {"applied": False, "statements": 0},
        "data": {"applied": False, "insert_statements": 0},
        "view": {"name": SALES_VIEW, "available": False},
        "training": {"applied": False, "counts": {}},
        "embeddings": {"applied": False, "summary": {}},
        "counts": {},
    }

    insert_statements = _load_insert_statements()
    schema_statements = _split_sql(_load_schema_sql())
    summary["schema"]["statements"] = len(schema_statements)
    summary["data"]["insert_statements"] = len(insert_statements)

    if options.dry_run:
        return summary

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_name(schema_name)}")
            if options.reset:
                _reset_sales_objects(cursor, schema_name)
            summary["schema"]["statements"] = _apply_schema(cursor, schema_name)
            summary["schema"]["applied"] = True
            summary["data"]["counts_by_statement"] = _apply_data(cursor, schema_name)
            summary["data"]["applied"] = True
            summary["counts"] = _count_rows(cursor, schema_name)
            summary["view"]["available"] = summary["counts"].get(SALES_VIEW, 0) >= 0

    embedder = None
    if options.run_training or options.run_embeddings:
        embedder = _get_embedder()

    if options.run_training:
        summary["training"]["counts"] = _train_sales_knowledge(tenant, embedder)
        summary["training"]["applied"] = True

    if options.run_embeddings:
        summary["embeddings"]["summary"] = sync_text_embeddings(
            tenant=tenant,
            embedder=embedder,
            table=SALES_VIEW,
        )
        summary["embeddings"]["applied"] = True

    return summary
