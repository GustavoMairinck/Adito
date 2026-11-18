from __future__ import annotations

import re
from typing import Iterable

import sqlglot
from sqlglot import exp

_DISALLOWED_EXP_NAMES = (
    "Alter",
    "Attach",
    "Clone",
    "Command",
    "Commit",
    "Copy",
    "Create",
    "Delete",
    "Describe",
    "Detach",
    "Drop",
    "Export",
    "Grant",
    "Insert",
    "Install",
    "Into",
    "Kill",
    "LoadData",
    "Merge",
    "Pragma",
    "Revoke",
    "Rollback",
    "Set",
    "Show",
    "Summarize",
    "Transaction",
    "TruncateTable",
    "Update",
    "Use",
)

DISALLOWED_EXPRESSIONS = tuple(
    cls for name in _DISALLOWED_EXP_NAMES if (cls := getattr(exp, name, None)) is not None
)

DISALLOWED_FUNCTIONS = frozenset({
    "read_csv",
    "read_csv_auto",
    "read_parquet",
    "read_json",
    "read_json_auto",
    "read_json_objects",
    "read_ndjson",
    "read_ndjson_auto",
    "read_ndjson_objects",
    "read_text",
    "read_blob",
    "parquet_scan",
    "csv_scan",
    "json_scan",
    "iceberg_scan",
    "delta_scan",
    "sqlite_scan",
    "postgres_scan",
    "mysql_scan",
    "duckdb_secrets",
    "duckdb_settings",
    "duckdb_databases",
    "duckdb_extensions",
    "duckdb_files",
    "glob",
    "getenv",
    "current_setting",
    "columns",
})

_DISALLOWED_LEADING_KEYWORDS = re.compile(
    r"^\s*(?:COPY|ATTACH|DETACH|INSTALL|LOAD|PRAGMA|SET|RESET|CALL|EXPORT|IMPORT|VACUUM|CHECKPOINT|DESCRIBE|SHOW|SUMMARIZE|EXPLAIN)\b",
    re.IGNORECASE,
)


def _normalize_sensitive_columns(
    sensitive_columns: Iterable[tuple[str, str] | str] | None,
    queried_tables: set[str],
) -> set[str]:
    """Retorna o conjunto de nomes de colunas sensíveis aplicáveis às tabelas consultadas."""
    blocked_cols: set[str] = set()
    if not sensitive_columns:
        return blocked_cols
    for item in sensitive_columns:
        if isinstance(item, tuple) and len(item) == 2:
            tbl, col = item[0].lower(), item[1].lower()
            if not queried_tables or tbl in queried_tables:
                blocked_cols.add(col)
        elif isinstance(item, str):
            blocked_cols.add(item.lower())
    return blocked_cols


def _extract_func_names(parsed: exp.Expression) -> set[str]:
    names: set[str] = set()
    for node in parsed.walk():
        if isinstance(node, exp.Anonymous):
            names.add((node.name or "").lower())
        elif isinstance(node, exp.Func):
            sql_name = getattr(node, "sql_name", None)
            if callable(sql_name):
                names.add(sql_name().lower())
            if getattr(node, "name", None):
                names.add(str(node.name).lower())
    return names - {""}


def validate_read_only_sql(
    sql: str,
    allowed_tables: set[str] | frozenset[str] | list[str],
    dialect: str = "sqlite",
    sensitive_columns: Iterable[tuple[str, str] | str] | None = None,
) -> tuple[bool, str | None]:
    """Primeira barreira (sintática via AST do sqlglot no dialeto SQLite).

    Garante:
    - Apenas uma instrução `SELECT` / `UNION`.
    - Nenhum comando de escrita, administração ou leitura de arquivos externos.
    - Apenas as tabelas/views fato listadas em `allowed_tables` (sem prefixo de schema proibido).
    - Nenhuma coluna sensível (`sensitive_columns`, CPF ou e-mail).
    """
    if not sql or not sql.strip():
        return False, "A consulta SQL está vazia."

    if _DISALLOWED_LEADING_KEYWORDS.match(sql):
        return False, "A consulta deve ser somente SELECT."

    allowed = {name.lower() for name in allowed_tables}
    try:
        expressions = sqlglot.parse(sql, read=dialect)
    except Exception:
        try:
            expressions = sqlglot.parse(sql, read="duckdb")
        except Exception as exc:
            return False, f"Sintaxe Inválida: {exc}"

    if len(expressions) != 1 or expressions[0] is None:
        return False, "A consulta deve conter exatamente uma instrução SQL."

    parsed = expressions[0]
    if not isinstance(parsed, (exp.Select, exp.Union)):
        return False, "A consulta deve ser somente SELECT."

    blocked = next(parsed.find_all(*DISALLOWED_EXPRESSIONS), None)
    if blocked is not None:
        return False, f"Operação não permitida: {blocked.key.upper()}."

    used_funcs = _extract_func_names(parsed)
    blocked_funcs = sorted(used_funcs & DISALLOWED_FUNCTIONS)
    if blocked_funcs:
        return False, f"Função não permitida no banco analítico: {', '.join(blocked_funcs)}."

    # Nomes de CTE aparecem como tabela no parse; não são relações físicas do banco.
    cte_names = {cte.alias_or_name.lower() for cte in parsed.find_all(exp.CTE)}
    table_nodes = [
        t for t in parsed.find_all(exp.Table) if (t.name or "").lower() not in cte_names
    ]

    for t in table_nodes:
        t_name = (t.name or "").lower()
        if t_name in DISALLOWED_FUNCTIONS or (
            isinstance(t.this, exp.Func) and t_name not in allowed
        ):
            return False, f"Função de leitura externa não permitida: {t_name or t.sql(dialect=dialect)}."
        schema_prefix = (t.db or "").lower()
        if schema_prefix:
            return False, f"Não use prefixo de schema ('{schema_prefix}.') nas views/tabelas fato."

    tables = {(t.name or "").lower() for t in table_nodes} - {""}
    if not tables or not tables <= allowed:
        found = ", ".join(sorted(tables)) or "nenhuma"
        expected = ", ".join(sorted(allowed))
        return (
            False,
            f"Relação inválida. Use somente: {expected}. Encontrado: {found}.",
        )

    blocked_cols = _normalize_sensitive_columns(sensitive_columns, tables)

    # Bloqueia SELECT * (e variantes como t.*, * EXCLUDE/REPLACE) incondicionalmente para evitar
    # vazamento caso uma tabela/view contenha coluna sensível não declarada em sensitive_columns.
    for star in parsed.find_all(exp.Star):
        if not isinstance(star.parent, exp.Count):
            return (
                False,
                "SELECT * não é permitido para proteger colunas sensíveis (LGPD). Liste as colunas explicitamente.",
            )

    for col in parsed.find_all(exp.Column):
        col_name = (col.name or "").lower()
        if not col_name:
            continue
        if col_name in blocked_cols or "cpf" in col_name or "email" in col_name:
            return False, f"Coluna sensível não permitida (LGPD): {col_name}."

    return True, None
