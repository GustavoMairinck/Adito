from core.datastore import connect_dados, default_read_policy
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
    dados_path: str | None,
    dialect: str,
    validate_sql: bool,
) -> dict[str, dict[str, object]]:
    sql = state["generated_sql"]
    log_node_start("validator", f"dados={dados_path or 'padrão'!r}")
    log_panel("bi", "SQL em validação", sql)

    if not validate_sql:
        log_warning("bi", "Validação SQL desativada por configuração.")
        log_node_end("validator", "valid=True")
        return {"validation_result": {"valid": True, "error": None}}

    policy = default_read_policy()
    is_safe, error = validate_read_only_sql(sql, dialect=dialect, allowed_tables=policy.exposed_views)
    if not is_safe:
        log_error("bi", f"Validação de segurança falhou: {error}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": error}}

    try:
        with connect_dados(policy, dados_path) as conn:
            conn.execute(f"EXPLAIN {sql}")
        log_success("bi", "SQL validado com EXPLAIN.")
        log_node_end("validator", "valid=True")
        return {"validation_result": {"valid": True, "error": None}}
    except Exception as exc:
        log_error("bi", f"Validação falhou no banco: {exc}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": f"Erro de Banco: {exc}"}}
