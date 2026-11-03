from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql as pg_sql
from core.rich_logging import (
    log_error,
    log_node_end,
    log_node_start,
    log_panel,
    log_success,
    log_warning,
)

from ..sql_security import validate_read_only_sql
from ..state import BiAgentState


def sql_validator(
    state: BiAgentState,
    dsn: str,
    dialect: str,
    validate_sql: bool,
) -> dict[str, dict[str, object]]:
    sql = state["generated_sql"]
    schema = state["db_schema_name"]
    log_node_start("validator", f"schema={schema!r}")
    log_panel("bi", "SQL em validação", sql)

    if not validate_sql:
        log_warning("bi", "Validação SQL desativada por configuração.")
        log_node_end("validator", "valid=True")
        return {"validation_result": {"valid": True, "error": None}}

    is_safe, error = validate_read_only_sql(sql, dialect=dialect)
    if not is_safe:
        log_error("bi", f"Validação de segurança falhou: {error}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": error}}

    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                if schema:
                    cur.execute(
                        pg_sql.SQL("SET search_path TO {}, public").format(
                            pg_sql.Identifier(schema)
                        )
                    )
                cur.execute(pg_sql.SQL("EXPLAIN {}").format(pg_sql.SQL(sql)))
        log_success("bi", "SQL validado com EXPLAIN.")
        log_node_end("validator", "valid=True")
        return {"validation_result": {"valid": True, "error": None}}
    except Exception as exc:
        log_error("bi", f"Validação falhou no banco: {exc}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": f"Erro de Banco: {exc}"}}
