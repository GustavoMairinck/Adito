import difflib
import re
import unicodedata

import sqlglot
from sqlglot import exp

from core.contexts import read_policy_for
from core.datastore import _like_to_regex, connect_dados
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

_MISSING_FIELD_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "coordenador_nome",
        (
            r"\bsem\s+coordenador\b",
            r"\bnao\s+(possuem|tem|possui|tiveram)\s+coordenador\b",
            r"\bcoordenador\s+(nao\s+informado|ausente|vazio)\b",
        ),
    ),
    (
        "programa_fomento",
        (
            r"\bsem\s+programa(\s+de\s+fomento)?\b",
            r"\bnao\s+(possuem|tem|possui)\s+programa(\s+de\s+fomento)?\b",
            r"\bprograma(\s+de\s+fomento)?\s+(nao\s+informado|nao\s+especificado|ausente)\b",
        ),
    ),
)

_EXCLUSION_PATTERNS: tuple[str, ...] = (
    r"\bexclua\b",
    r"\bexcluindo\b",
    r"\bexceto\b",
    r"\bdesconsidere\b",
    r"\bignore\b",
    r"\bapenas\s+com\b",
    r"\bsomente\s+com\b",
)

_EMPTY_TEXT_MARKERS: frozenset[str] = frozenset({
    "",
    "nao informado",
    "nao informada",
    "nao especificado",
    "nao especificada",
    "sem informacao",
})


def _norm_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _column_matches(node: exp.Expression, col_name: str) -> bool:
    for col in node.find_all(exp.Column):
        if (col.name or "").lower() == col_name:
            return True
    return False


def _filter_clauses(tree: exp.Expression) -> list[exp.Expression]:
    return [*tree.find_all(exp.Where), *tree.find_all(exp.Having)]


def _has_null_handling(tree: exp.Expression, col_name: str) -> bool:
    for clause in _filter_clauses(tree):
        for is_node in clause.find_all(exp.Is):
            if (
                not isinstance(is_node.parent, exp.Not)
                and isinstance(is_node.expression, exp.Null)
                and _column_matches(is_node.this, col_name)
            ):
                return True
        for coal_node in clause.find_all(exp.Coalesce):
            if _column_matches(coal_node, col_name):
                return True
    return False


def _filters_column_only_by_empty_text(tree: exp.Expression, col_name: str) -> bool:
    for clause in _filter_clauses(tree):
        for eq_node in clause.find_all(exp.EQ):
            for side, other in ((eq_node.this, eq_node.expression), (eq_node.expression, eq_node.this)):
                if _column_matches(side, col_name) and isinstance(other, exp.Literal) and other.is_string:
                    if _norm_text(other.this) in _EMPTY_TEXT_MARKERS:
                        return True
        for like_node in clause.find_all((exp.Like, exp.ILike)):
            if _column_matches(like_node.this, col_name) and isinstance(like_node.expression, exp.Literal) and like_node.expression.is_string:
                if _norm_text(like_node.expression.this.strip("%")) in _EMPTY_TEXT_MARKERS:
                    return True
        for in_node in clause.find_all(exp.In):
            if _column_matches(in_node.this, col_name):
                for arg in in_node.expressions or []:
                    if isinstance(arg, exp.Literal) and arg.is_string and _norm_text(arg.this) in _EMPTY_TEXT_MARKERS:
                        return True
    return False


def check_missing_null_guard(question: str, sql: str, dialect: str = "sqlite") -> str | None:
    """Garante checagem de IS NULL quando a pergunta pede registros ausentes e a SQL testa só strings."""
    q_norm = _norm_text(question)
    if not q_norm or any(re.search(pat, q_norm) for pat in _EXCLUSION_PATTERNS):
        return None

    target_cols = [
        col for col, patterns in _MISSING_FIELD_PATTERNS
        if any(re.search(pat, q_norm) for pat in patterns)
    ]
    if not target_cols:
        return None

    try:
        tree = sqlglot.parse_one(sql, read=dialect)
    except Exception:
        return None

    for col in target_cols:
        if _filters_column_only_by_empty_text(tree, col) and not _has_null_handling(tree, col):
            return (
                f"A consulta filtra registros sem '{col}' apenas por texto padronizado/vazio, "
                f"ignorando valores NULL reais. Inclua '{col} IS NULL' na condição."
            )
    return None


def _coluna_comparada(node: exp.Expression) -> str | None:
    """Nome da coluna em `col`, `LOWER(col)`, `UPPER(col)` ou `TRIM(col)`."""
    while isinstance(node, (exp.Lower, exp.Upper, exp.Trim)):
        node = node.this
    return (node.name or "").lower() if isinstance(node, exp.Column) else None


def _literais_de_texto(tree: exp.Expression):
    """(coluna, literal, é_like) de cada filtro de texto em WHERE/HAVING."""
    for clause in _filter_clauses(tree):
        for node in clause.find_all(exp.EQ, exp.Like, exp.ILike, exp.In):
            if isinstance(node, exp.In):
                coluna = _coluna_comparada(node.this)
                literais = [a for a in node.expressions or [] if isinstance(a, exp.Literal) and a.is_string]
                if coluna:
                    for lit in literais:
                        yield coluna, lit.this, False
                continue
            for lado, outro in ((node.this, node.expression), (node.expression, node.this)):
                coluna = _coluna_comparada(lado)
                if coluna and isinstance(outro, exp.Literal) and outro.is_string:
                    yield coluna, outro.this, not isinstance(node, exp.EQ)
                    break


def check_valores_inexistentes(sql: str, catalogo: dict, views: set[str], dialect: str = "sqlite") -> str | None:
    """Aponta filtros de texto cujo valor não existe no dados.db, com os valores reais mais próximos.

    Só olha colunas com vetores no índice (embed_columns). Comparação sem acento e sem caixa, como
    o LIKE do Adito; colunas agregadas com "; " passam se cada parte existir.
    """
    if not catalogo:
        return None
    try:
        tree = sqlglot.parse_one(sql, read=dialect)
    except Exception:
        return None
    problemas = []
    for coluna, literal, e_like in _literais_de_texto(tree):
        conhecidos: dict[str, str] = {}
        for (view, col), valores in catalogo.items():
            if col.lower() == coluna and view in views:
                conhecidos.update(valores)
        if not conhecidos or not literal.strip("% "):
            continue
        alvo = _norm_text(literal)
        if e_like:
            rx = _like_to_regex(alvo)
            existe = any(rx.match(v) for v in conhecidos)
        else:
            partes = [_norm_text(p) for p in literal.split("; ")]
            existe = alvo in conhecidos or all(p in conhecidos for p in partes)
        if existe:
            continue
        proximos = difflib.get_close_matches(alvo.strip("%"), list(conhecidos), n=3, cutoff=0.6)
        sugestao = ", ".join(f"'{conhecidos[p]}'" for p in proximos) or "nenhum parecido"
        problemas.append(f"'{literal}' não existe em {coluna} (valores próximos: {sugestao})")
    if not problemas:
        return None
    return (
        "Filtro com valor que não existe no banco: " + "; ".join(problemas)
        + ". Use o valor real mais próximo se ele corresponder à pergunta; se nenhum corresponder, mantenha o filtro."
    )


def sql_validator(
    state: BiAgentState,
    dados_path: str | None,
    dialect: str,
    validate_sql: bool,
) -> dict[str, dict[str, object]]:
    sql = state["generated_sql"]
    log_node_start("validator", f"contexto={state.get('contexto_id')!r}")
    log_panel("bi", "SQL em validação", sql)

    if not validate_sql:
        log_warning("bi", "Validação SQL desativada por configuração.")
        log_node_end("validator", "valid=True")
        return {"validation_result": {"valid": True, "error": None}}

    policy = read_policy_for(state.get("contexto_id"))
    if not policy.exposed_views:
        log_error("bi", "Sem contexto: nenhuma view exposta.")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": "Nenhum contexto de dados selecionado."}}
    is_safe, error = validate_read_only_sql(
        sql,
        policy.exposed_views,
        dialect=dialect,
        sensitive_columns=policy.sensitive_columns,
    )
    if not is_safe:
        log_error("bi", f"Validação de segurança falhou: {error}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": error}}

    try:
        with connect_dados(policy, dados_path) as conn:
            conn.execute(f"EXPLAIN {sql}")
        log_success("bi", "SQL validado com EXPLAIN.")
    except Exception as exc:
        log_error("bi", f"Validação falhou no banco: {exc}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": f"Erro de Banco: {exc}"}}

    question = state.get("user_input", "")
    semantic_error = check_missing_null_guard(question, sql, dialect=dialect)
    if semantic_error:
        log_warning("bi", f"Validação semântica (NULL guard) falhou: {semantic_error}")
        log_node_end("validator", "valid=False")
        return {"validation_result": {"valid": False, "error": semantic_error}}

    # Uma chance só: se o valor pedido de fato não existe, a segunda tentativa passa e o resultado
    # vazio mostra "nenhum registro" em vez de "não foi possível gerar a consulta".
    if not state.get("correction_attempts"):
        from analytics_index.valores import indice_valores

        indice = indice_valores()
        valor_error = check_valores_inexistentes(
            sql, indice.catalogo() if indice.disponivel else {}, set(policy.exposed_views), dialect=dialect
        )
        if valor_error:
            log_warning("bi", f"Validação de valores falhou: {valor_error}")
            log_node_end("validator", "valid=False")
            return {"validation_result": {"valid": False, "error": valor_error}}

    log_node_end("validator", "valid=True")
    return {"validation_result": {"valid": True, "error": None}}
