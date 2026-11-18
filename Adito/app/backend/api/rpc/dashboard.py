"""Painel (KPIs e gráficos fixos) e widgets do "Meu dashboard"."""
import json
from decimal import Decimal

from agents.bi_agent.agent import execute_query
from core import db
from core.contexts import pick_contexto
from core.datastore import connect_dados
from core.db import api_dt, to_db_id
from core.records import CHART_TYPES, WIDGET_MODES, Contexto, Dashboard, Widget, delete_widget
from core.rich_logging import log_error, log_info, log_success

from .errors import not_found
from .params import Choice, Field, Int, Str, validate
from .registry import rpc
from .session import current

ANALYTICS_VIEW = "vfact_orientacao_bolsa_resolved"

# Colunas de filtro devolvidas como lista ou JSON.
_JSON_COLUMNS = frozenset({
    "anos_disponiveis", "areas_disponiveis", "modalidades_disponiveis", "statuses_disponiveis",
})


def _filters(params):
    mapping = {
        "ano": ("ano", "="),
        "area": ("grande_area", "ilike"),
        "modalidade": ("programa_fomento", "ilike"),
        "status": ("modalidade", "ilike"),
        "projeto": ("titulo_projeto", "ilike"),
    }
    clauses, values = [], []
    for key, (column, op) in mapping.items():
        value = params.get(key)
        if not value:
            continue
        if op == "=":
            clauses.append(f"{column} = ?")
            values.append(value)
        else:
            clauses.append(f"{column} ILIKE ?")
            values.append(f"%{value}%")
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


def _fetchall(query, values=None, json_columns=frozenset()):
    with connect_dados() as conn:
        rows = [dict(row) for row in conn.execute(query, values or []).fetchall()]
    for row in rows:
        for key in json_columns & row.keys():
            if isinstance(row[key], str):
                row[key] = json.loads(row[key])
    return rows


def _fetchone(query, values=None, json_columns=frozenset()):
    rows = _fetchall(query, values, json_columns)
    return rows[0] if rows else {}


def _money(value):
    value = value or Decimal("0")
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@rpc("dashboard.kpis")
def kpis(params):
    where, values = _filters(params)
    return _fetchone(f"""
        SELECT
          COALESCE(SUM(investimento_total_estimado), 0) AS total_investido,
          COUNT(DISTINCT titulo_projeto) AS projetos_ativos,
          COALESCE(SUM(CASE WHEN ano = ? THEN investimento_total_estimado ELSE 0 END), 0) AS pagamentos_ano_vigente,
          COUNT(DISTINCT nome_orientador) AS equipe_alocada
        FROM {ANALYTICS_VIEW}
        {where}
    """, [db.utcnow().year, *values])


@rpc("dashboard.top_projects")
def top_projects(params):
    where, values = _filters(params)
    rows = _fetchall(f"""
        SELECT
          titulo_projeto AS nome,
          COALESCE(SUM(investimento_total_estimado), 0) AS valor,
          MAX(programa_fomento) AS status
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY titulo_projeto
        ORDER BY valor DESC
        LIMIT 10
    """, values)
    for row in rows:
        row["valor_formatado"] = _money(row["valor"])
    return rows


@rpc("dashboard.charts")
def charts(params):
    where, values = _filters(params)
    por_ano = _fetchall(f"""
        SELECT ano AS year, COALESCE(SUM(investimento_total_estimado), 0) AS value
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY ano
        ORDER BY ano
    """, values)
    mensal = _fetchall(f"""
        SELECT COALESCE(EXTRACT(MONTH FROM data_inicio)::INTEGER, 1) AS month_num,
               CAST(COALESCE(EXTRACT(MONTH FROM data_inicio)::INTEGER, 1) AS VARCHAR) AS month,
               COALESCE(SUM(investimento_total_estimado), 0) AS value
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY month_num, month
        ORDER BY month_num
    """, values)
    filters = _fetchone(f"""
        SELECT
          COALESCE(list(DISTINCT ano) FILTER (WHERE ano IS NOT NULL), []) AS anos_disponiveis,
          COALESCE(list(DISTINCT grande_area) FILTER (WHERE grande_area IS NOT NULL), []) AS areas_disponiveis,
          COALESCE(list(DISTINCT programa_fomento) FILTER (WHERE programa_fomento IS NOT NULL), []) AS modalidades_disponiveis,
          COALESCE(list(DISTINCT modalidade) FILTER (WHERE modalidade IS NOT NULL), []) AS statuses_disponiveis,
          COALESCE(MAX(ano), EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER) AS ano_vigente
        FROM {ANALYTICS_VIEW}
    """, json_columns=_JSON_COLUMNS)
    return {"por_ano": por_ano, "mensal": mensal, **filters}


# ── Widgets ─────────────────────────────────────────────────────────────────

class _ContextoRef(Field):
    def convert(self, value):
        try:
            contexto = Contexto.first("id = ?", [to_db_id(value)])
        except (ValueError, TypeError, AttributeError):
            contexto = None
        if contexto is None:
            raise ValueError(f'Invalid pk "{value}" - object does not exist.')
        return contexto.id


WIDGET_FIELDS = {
    "title": Str(required=True, max_length=255, allow_blank=False),
    "question_original": Str(required=True, allow_blank=False),
    "sql_validated": Str(),
    "chart_type": Choice(required=True, choices=CHART_TYPES),
    "mode": Choice(choices=WIDGET_MODES),
    "cache_ttl_hours": Int(),
    "size": Str(max_length=50, allow_blank=False),
    "grid_x": Int(),
    "grid_y": Int(),
    "grid_w": Int(),
    "grid_h": Int(),
    "limit_rows": Int(),
    "sort_order": Str(max_length=50, allow_blank=False),
    "status": Str(max_length=50, allow_blank=False),
    "contexto": _ContextoRef(allow_null=True),
}


def widget_json(widget: Widget) -> dict:
    return {
        "id": widget.id,
        "title": widget.title,
        "question_original": widget.question_original,
        "sql_validated": widget.sql_validated,
        "chart_type": widget.chart_type,
        "mode": widget.mode,
        "cache_ttl_hours": widget.cache_ttl_hours,
        "size": widget.size,
        "grid_x": widget.grid_x,
        "grid_y": widget.grid_y,
        "grid_w": widget.grid_w,
        "grid_h": widget.grid_h,
        "limit_rows": widget.limit_rows,
        "sort_order": widget.sort_order,
        "status": widget.status,
        "last_executed_at": api_dt(widget.last_executed_at),
        "created_at": api_dt(widget.created_at),
        "updated_at": api_dt(widget.updated_at),
        "dashboard": widget.dashboard_id,
        "contexto": widget.contexto_id,
    }


def _owner_ids():
    user, tenant = current()
    return [to_db_id(tenant.id) if tenant else None, to_db_id(user.id)]


_MEUS = "dashboard_id IN (SELECT id FROM dashboard_dashboard WHERE tenant_id = ? AND user_id = ?)"


def _widget(params) -> Widget:
    try:
        wid = to_db_id(params.get("id"))
    except (ValueError, TypeError, AttributeError):
        wid = None
    widget = Widget.first(f"id = ? AND {_MEUS}", [wid, *_owner_ids()]) if wid else None
    if widget is None:
        raise not_found("Widget")
    return widget


def _default_dashboard() -> Dashboard:
    user, tenant = current()
    tid, uid = _owner_ids()
    with db.transaction():
        dashboard = Dashboard.first("user_id = ? AND tenant_id = ? AND name = ?", [uid, tid, "principal"])
        if dashboard is None:
            dashboard = Dashboard(
                user_id=user.id, tenant_id=tenant.id if tenant else None,
                name="principal", description="Dashboard pessoal padrão",
            ).insert()
    return dashboard


def _apply(widget: Widget, data: dict) -> None:
    for name, value in data.items():
        setattr(widget, "contexto_id" if name == "contexto" else name, value)


@rpc("widgets.list")
def widgets_list(params):
    return [widget_json(w) for w in Widget.select(_MEUS, _owner_ids())]


@rpc("widgets.create")
def widgets_create(params):
    data = validate(WIDGET_FIELDS, params)
    _, tenant = current()
    dashboard = _default_dashboard()
    # Sem contexto explícito, usa o único ativo; o SQL do widget só roda com a política dele.
    if not data.get("contexto"):
        contexto = pick_contexto(tenant) if tenant else None
        data["contexto"] = contexto.id if contexto else None
    data.setdefault("sql_validated", "")
    widget = Widget(dashboard_id=dashboard.id)
    _apply(widget, data)
    return widget_json(widget.insert())


@rpc("widgets.update")
def widgets_update(params):
    widget = _widget(params)
    data = validate(WIDGET_FIELDS, {k: v for k, v in params.items() if k != "id"}, partial=True)
    _apply(widget, data)
    return widget_json(widget.update())


@rpc("widgets.delete")
def widgets_delete(params):
    delete_widget(_widget(params).id)
    return None


@rpc("widgets.refresh")
def widgets_refresh(params):
    """Re-executa o SQL do widget no banco analítico."""
    widget = _widget(params)
    log_info("dashboard", f"Atualizando widget id={widget.id} sql={widget.sql_validated[:100]!r}")
    # limit_rows=0 significa todas as linhas: o dashboard precisa do resultado completo.
    data = execute_query(widget.sql_validated, contexto_id=widget.contexto_id, max_rows=widget.limit_rows or None)
    if data and isinstance(data, list) and data[0].get("error"):
        log_error("dashboard", f"Erro na query do widget {widget.id}: {data[0]['error']!r}")
        widget.status = "BROKEN"
    else:
        log_success("dashboard", f"Widget {widget.id} atualizado: {len(data)} linhas")
        widget.status = "OK"
    widget.last_executed_at = db.utcnow()
    widget.update("status", "last_executed_at")
    return {"data": data, "widget_status": widget.status}

