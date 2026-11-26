"""Catálogo e consultas locais das relações expostas pelos contextos (tela Explorar)."""
import logging
import re
import sqlite3

from core.contexts import read_policy_for, visible_columns
from core.datastore import connect_dados
from core.db import to_db_id
from core.records import Contexto

from .errors import ApiError, bad_request, not_found
from .params import Choice, Int, Str, Uuid, validate
from .registry import rpc
from .session import current

logger = logging.getLogger(__name__)

CATALOG = {"contexto_id": Uuid(required=True)}
ROWS = {
    **CATALOG,
    "table": Str(required=True, max_length=255, allow_blank=False),
    "search": Str(default="", max_length=200),
    "filter_column": Str(default=""),
    "filter_value": Str(default="", max_length=200),
    "sort": Str(default=""),
    "direction": Choice(choices=("asc", "desc"), default="asc"),
    "page": Int(min_value=1, default=1),
    "page_size": Choice(choices=(25, 50, 100), default=25),
    "group_by": Str(default=""),
}


def _contexto(params) -> Contexto:
    _, tenant = current()
    contexto = Contexto.first(
        "id = ? AND tenant_id = ? AND is_active = 1",
        [to_db_id(params["contexto_id"]), to_db_id(tenant.id) if tenant else None],
    )
    if contexto is None:
        raise not_found("Contexto")
    return contexto


def _quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def _kind(view):
    if view.get("kind") in {"fact", "dimension", "entity"}:
        return view["kind"]
    name = re.sub(r"^(?:vw_|v_|v(?=fact|fato))", "", view["name"].lower())
    if name.startswith(("fact", "fato")):
        return "fact"
    if name.startswith(("dim_", "dimensao_")):
        return "dimension"
    return "entity"


def _unavailable():
    return ApiError(503, {
        "detail": "Não foi possível ler os dados. Verifique o dados.db e recarregue os contextos em Administração.",
    })


@rpc("explorer.tables")
def tables(params):
    contexto = _contexto(validate(CATALOG, params))
    catalog = []
    try:
        for view in contexto.views:
            columns = visible_columns(contexto, view["name"])
            catalog.append({
                "name": view["name"],
                "label": view.get("label") or view["name"],
                "description": view.get("description", ""),
                "kind": _kind(view),
                "columns": [{"name": name, "type": kind} for name, kind in columns],
                "available": bool(columns),
            })
    except (FileNotFoundError, sqlite3.Error):
        logger.exception("Falha ao ler o catálogo do contexto %s", contexto.id)
        raise _unavailable() from None
    return {"tables": catalog}


@rpc("explorer.rows")
def rows(params):
    params = validate(ROWS, params)
    contexto = _contexto(params)
    view = contexto.view_config(params["table"])
    if view is None:
        raise ApiError(404, {"detail": "Tabela indisponível neste contexto."})

    try:
        columns = [name for name, _ in visible_columns(contexto, view["name"])]
        if not columns:
            raise bad_request({"detail": "Esta tabela não possui colunas disponíveis para consulta."})
        for key in ("sort", "filter_column", "group_by"):
            if params[key] and params[key] not in columns:
                raise bad_request({key: "Selecione uma coluna disponível."})
        if params["filter_value"] and not params["filter_column"]:
            raise bad_request({"filter_column": "Selecione a coluna do filtro."})

        clauses, values = [], []
        if params["search"]:
            # A busca trata %, _ e ! como texto literal (LIKE com custom_like é case e acento-insensível).
            search = params["search"].replace("!", "!!").replace("%", "!%").replace("_", "!_")
            clauses.append("(" + " OR ".join(
                f"CAST({_quote(column)} AS TEXT) LIKE ? ESCAPE '!'" for column in columns
            ) + ")")
            values.extend([f"%{search}%"] * len(columns))
        if params["filter_column"] and params["filter_value"]:
            clauses.append(f'CAST({_quote(params["filter_column"])} AS TEXT) = ?')
            values.append(params["filter_value"])

        source = _quote(view["name"])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sort = params["sort"] or columns[0]
        null_order = "NULLS FIRST" if params["direction"] == "asc" else "NULLS LAST"
        order = ", ".join([
            f'{_quote(sort)} {params["direction"].upper()} {null_order}',
            *[f"{_quote(column)} ASC {null_order}" for column in columns if column != sort],
        ])
        page_size = int(params["page_size"])
        # O SQL usa apenas a relação e as colunas já validadas no contexto.
        # Os valores fornecidos pelo usuário são parâmetros da consulta.
        with connect_dados(read_policy_for(contexto)) as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM {source}{where}", values).fetchone()[0]
            page = min(params["page"], max(1, (total + page_size - 1) // page_size))
            records = conn.execute(
                f'SELECT {", ".join(map(_quote, columns))} FROM {source}{where} '
                f"ORDER BY {order} LIMIT ? OFFSET ?",
                [*values, page_size, (page - 1) * page_size],
            ).fetchall()
            distribution = []
            if params["group_by"]:
                group = _quote(params["group_by"])
                distribution = [_record(row) for row in conn.execute(
                    f"SELECT {group} AS value, COUNT(*) AS count FROM {source}{where} "
                    f"GROUP BY {group} ORDER BY COUNT(*) DESC, {group} LIMIT 12", values,
                )]
        return {
            "rows": [_record(record) for record in records],
            "total": total, "page": page, "page_size": page_size,
            "distribution": distribution,
        }
    except (FileNotFoundError, PermissionError, sqlite3.Error):
        logger.exception("Falha ao consultar a relação %s do contexto %s", view["name"], contexto.id)
        raise _unavailable() from None


def _record(row):
    return {
        key: "0x" + bytes(value).hex() if isinstance(value, (bytes, bytearray, memoryview)) else value
        for key, value in dict(row).items()
    }
