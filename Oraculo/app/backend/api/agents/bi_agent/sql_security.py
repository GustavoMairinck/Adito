import sqlglot
from sqlglot import exp

from .config import DEFAULT_SOURCE_TABLE


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


def validate_read_only_sql(sql: str, dialect: str = "postgres") -> tuple[bool, str | None]:
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

    tables = {table.name.lower() for table in parsed.find_all(exp.Table)}
    if tables != {DEFAULT_SOURCE_TABLE}:
        found = ", ".join(sorted(tables)) or "nenhuma"
        return (
            False,
            f"Relação inválida. Use somente a tabela {DEFAULT_SOURCE_TABLE}. Encontrado: {found}.",
        )

    return True, None
