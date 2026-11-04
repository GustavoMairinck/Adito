import sqlglot
from sqlglot import exp

DISALLOWED_EXPRESSIONS = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Into,
    exp.Merge,
    exp.Update,
)


def validate_read_only_sql(
    sql: str,
    allowed_tables: set[str] | frozenset[str] | list[str],
    dialect: str = "sqlite",
) -> tuple[bool, str | None]:
    """Primeira barreira (sintática). A segunda é o authorizer do dados.db."""
    allowed = {name.lower() for name in allowed_tables}
    try:
        expressions = sqlglot.parse(sql, read=dialect)
    except Exception as exc:
        return False, f"Sintaxe Inválida: {exc}"

    if len(expressions) != 1:
        return False, "A consulta deve conter exatamente uma instrução SQL."

    parsed = expressions[0]
    if not isinstance(parsed, (exp.Select, exp.Union)):
        return False, "A consulta deve ser somente SELECT."

    blocked = next(parsed.find_all(*DISALLOWED_EXPRESSIONS), None)
    if blocked is not None:
        return False, f"Operação não permitida: {blocked.key.upper()}."

    # Nomes de CTE aparecem como tabela no parse; não são relações do banco.
    cte_names = {cte.alias_or_name.lower() for cte in parsed.find_all(exp.CTE)}
    tables = {table.name.lower() for table in parsed.find_all(exp.Table)} - cte_names
    if not tables or not tables <= allowed:
        found = ", ".join(sorted(tables)) or "nenhuma"
        expected = ", ".join(sorted(allowed))
        return (
            False,
            f"Relação inválida. Use somente: {expected}. Encontrado: {found}.",
        )

    return True, None
