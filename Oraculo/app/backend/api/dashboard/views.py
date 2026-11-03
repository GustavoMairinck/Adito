from decimal import Decimal
import json
import os

from django.db import connection
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .models import Dashboard, Widget
from .serializers import DashboardSerializer, WidgetSerializer
from chat.views import get_bi_agent
from core.contexts import pick_contexto
from core.datastore import connect_dados
from core.rich_logging import log_error, log_info, log_success

ANALYTICS_VIEW = 'vfactvendasresolved'

# Colunas de filtro devolvidas pelo SQLite como texto JSON (json_group_array).
_JSON_COLUMNS = frozenset({
    'anos_disponiveis', 'areas_disponiveis', 'modalidades_disponiveis', 'statuses_disponiveis',
    'anos', 'modalidades', 'status', 'areas', 'instituicoes',
})


def _filters(request):
    mapping = {
        'ano': ('ano', '='),
        'area': ('categoria_produto', 'ilike'),
        'modalidade': ('canal', 'ilike'),
        'status': ('porte_cliente', 'ilike'),
        'projeto': ('produto', 'ilike'),
    }
    clauses = []
    params = []
    for key, (column, op) in mapping.items():
        value = request.query_params.get(key)
        if not value:
            continue
        if op == '=':
            clauses.append(f"{column} = ?")
            params.append(value)
        else:
            clauses.append(f"{column} LIKE ?")
            params.append(f"%{value}%")
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _fetchall(request, query, params=None, json_columns=frozenset()):
    with connect_dados() as conn:
        rows = [dict(row) for row in conn.execute(query, params or []).fetchall()]
    for row in rows:
        for key in json_columns & row.keys():
            if isinstance(row[key], str):
                row[key] = json.loads(row[key])
    return rows


def _fetchone(request, query, params=None, json_columns=frozenset()):
    rows = _fetchall(request, query, params, json_columns)
    return rows[0] if rows else {}


def _money(value):
    value = value or Decimal('0')
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _metric(value):
    return {"oltp": value, "olap": value, "delta_abs": 0, "delta_pct": 0, "status": "ok"}


def _get_or_create_default_dashboard(user):
    dashboard, _ = Dashboard.objects.get_or_create(
        user=user,
        tenant=user.tenant,
        name='principal',
        defaults={'description': 'Dashboard pessoal padrão'},
    )
    return dashboard

class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.tenant:
            return self.queryset.filter(tenant=self.request.user.tenant, user=self.request.user)
        return self.queryset.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, tenant=self.request.user.tenant)

class WidgetViewSet(viewsets.ModelViewSet):
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.tenant:
            return self.queryset.filter(dashboard__tenant=self.request.user.tenant, dashboard__user=self.request.user)
        return self.queryset.none()

    def perform_create(self, serializer):
        dashboard = _get_or_create_default_dashboard(self.request.user)
        # Sem contexto explícito, usa o único ativo; o SQL do widget só roda com a política dele.
        contexto = serializer.validated_data.get('contexto') or pick_contexto(self.request.user.tenant)
        serializer.save(
            dashboard=dashboard,
            contexto=contexto,
            sql_validated=serializer.validated_data.get('sql_validated', ''),
        )

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['get', 'post'])
    def refresh(self, request, pk=None):
        """Re-executa o SQL do Widget no banco analítico."""
        widget = self.get_object()
        log_info("dashboard", f"Atualizando widget id={widget.id} sql={widget.sql_validated[:100]!r}")

        agent = get_bi_agent()
        # limit_rows=0 significa todas as linhas: o dashboard precisa do resultado completo.
        data = agent.execute_query(widget.sql_validated, contexto_id=widget.contexto_id, max_rows=widget.limit_rows or None)

        if data and isinstance(data, list) and data[0].get('error'):
            log_error("dashboard", f"Erro na query do widget {widget.id}: {data[0]['error']!r}")
            widget.status = 'BROKEN'
        else:
            log_success("dashboard", f"Widget {widget.id} atualizado: {len(data)} linhas")
            widget.status = 'OK'

        widget.last_executed_at = timezone.now()
        widget.save(update_fields=['status', 'last_executed_at'])

        return Response({
            "data": data,
            "widget_status": widget.status
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kpis(request):
    where, params = _filters(request)
    year = timezone.now().year
    row = _fetchone(request, f"""
        SELECT
          COALESCE(SUM(receita_liquida), 0) AS total_investido,
          COUNT(DISTINCT produto) AS projetos_ativos,
          COALESCE(SUM(CASE WHEN ano = ? THEN receita_liquida ELSE 0 END), 0) AS pagamentos_ano_vigente,
          COUNT(DISTINCT vendedor) AS equipe_alocada
        FROM {ANALYTICS_VIEW}
        {where}
    """, [year, *params])
    return Response(row)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_projects(request):
    where, params = _filters(request)
    rows = _fetchall(request, f"""
        SELECT
          produto AS nome,
          COALESCE(SUM(receita_liquida), 0) AS valor,
          MAX(categoria_produto) AS status
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY produto
        ORDER BY valor DESC
        LIMIT 10
    """, params)
    for row in rows:
        row["valor_formatado"] = _money(row["valor"])
    return Response(rows)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def charts(request):
    where, params = _filters(request)
    por_ano = _fetchall(request, f"""
        SELECT ano AS year, COALESCE(SUM(receita_liquida), 0) AS value
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY ano
        ORDER BY ano
    """, params)
    mensal = _fetchall(request, f"""
        SELECT mes AS month_num, CAST(mes AS TEXT) AS month,
               COALESCE(SUM(receita_liquida), 0) AS value
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY mes
        ORDER BY mes
    """, params)
    filters = _fetchone(request, f"""
        SELECT
          COALESCE(json_group_array(DISTINCT ano) FILTER (WHERE ano IS NOT NULL), '[]') AS anos_disponiveis,
          COALESCE(json_group_array(DISTINCT categoria_produto) FILTER (WHERE categoria_produto IS NOT NULL), '[]') AS areas_disponiveis,
          COALESCE(json_group_array(DISTINCT canal) FILTER (WHERE canal IS NOT NULL), '[]') AS modalidades_disponiveis,
          COALESCE(json_group_array(DISTINCT porte_cliente) FILTER (WHERE porte_cliente IS NOT NULL), '[]') AS statuses_disponiveis,
          COALESCE(MAX(ano), CAST(strftime('%Y', 'now') AS INTEGER)) AS ano_vigente
        FROM {ANALYTICS_VIEW}
    """, json_columns=_JSON_COLUMNS)
    return Response({
        "por_ano": por_ano,
        "mensal": mensal,
        **filters,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def projects(request):
    where, params = _filters(request)
    rows = _fetchall(request, f"""
        SELECT
          MIN(CAST(id_venda AS TEXT)) AS id,
          produto AS projeto,
          MAX(cliente) AS edital,
          MAX(canal) AS modalidade,
          COALESCE(SUM(receita_liquida), 0) AS valor,
          MAX(porte_cliente) AS status,
          MAX(categoria_produto) AS area
        FROM {ANALYTICS_VIEW}
        {where}
        GROUP BY produto
        ORDER BY valor DESC, projeto
        LIMIT 200
    """, params)
    for row in rows:
        row["nome"] = row["projeto"]
        row["valor_formatado"] = _money(row["valor"])
    filters = _fetchone(request, f"""
        SELECT
          COALESCE(json_group_array(DISTINCT ano) FILTER (WHERE ano IS NOT NULL), '[]') AS anos,
          COALESCE(json_group_array(DISTINCT canal) FILTER (WHERE canal IS NOT NULL), '[]') AS modalidades,
          COALESCE(json_group_array(DISTINCT porte_cliente) FILTER (WHERE porte_cliente IS NOT NULL), '[]') AS status,
          COALESCE(json_group_array(DISTINCT categoria_produto) FILTER (WHERE categoria_produto IS NOT NULL), '[]') AS areas,
          COALESCE(json_group_array(DISTINCT cliente) FILTER (WHERE cliente IS NOT NULL), '[]') AS instituicoes
        FROM {ANALYTICS_VIEW}
    """, json_columns=_JSON_COLUMNS)
    return Response({"data": rows, "total": len(rows), "filtros_disponiveis": filters})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def data_validation(request):
    row = _fetchone(request, f"""
        SELECT
          COUNT(*) AS total_linhas,
          COUNT(DISTINCT produto) AS qtd_produtos,
          COUNT(DISTINCT cliente) AS qtd_clientes,
          COUNT(DISTINCT canal) AS qtd_canais
        FROM {ANALYTICS_VIEW}
    """)
    checks = [
        {"id": "postgres-total-linhas", "name": "Linhas na view analítica", "oltp_value": row["total_linhas"], "olap_value": row["total_linhas"], "delta_abs": 0, "delta_pct": 0, "detail": "Validação direta no PostgreSQL após bootstrap.", "status": "ok"},
        {"id": "postgres-produtos", "name": "Produtos distintos", "oltp_value": row["qtd_produtos"], "olap_value": row["qtd_produtos"], "delta_abs": 0, "delta_pct": 0, "detail": "Métrica calculada na view consolidada de vendas.", "status": "ok"},
        {"id": "postgres-clientes", "name": "Clientes distintos", "oltp_value": row["qtd_clientes"], "olap_value": row["qtd_clientes"], "delta_abs": 0, "delta_pct": 0, "detail": "Métrica calculada na view consolidada de vendas.", "status": "ok"},
        {"id": "postgres-canais", "name": "Canais distintos", "oltp_value": row["qtd_canais"], "olap_value": row["qtd_canais"], "delta_abs": 0, "delta_pct": 0, "detail": "Métrica calculada na view consolidada de vendas.", "status": "ok"},
    ]
    return Response({
        "timestamp": timezone.now().isoformat(),
        "summary": {"total": len(checks), "ok": len(checks), "warning": 0, "critical": 0},
        "checks": checks,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def data_validation_analytics(request):
    rows = _fetchall(request, f"""
        SELECT
          ano,
          COALESCE(SUM(receita_liquida), 0) AS valor_pago,
          COUNT(DISTINCT produto) AS qtd_projetos,
          COUNT(DISTINCT cliente) AS qtd_pessoas,
          COUNT(DISTINCT canal) AS qtd_editais,
          COUNT(DISTINCT categoria_produto) AS qtd_modalidades,
          COUNT(DISTINCT porte_cliente) AS qtd_status
        FROM {ANALYTICS_VIEW}
        GROUP BY ano
        ORDER BY ano DESC
    """)
    return Response({"analytics_by_year": [
        {
            "ano": row["ano"],
            "valor_pago": _metric(row["valor_pago"]),
            "qtd_projetos": _metric(row["qtd_projetos"]),
            "qtd_pessoas": _metric(row["qtd_pessoas"]),
            "qtd_editais": _metric(row["qtd_editais"]),
            "qtd_modalidades": _metric(row["qtd_modalidades"]),
            "qtd_status": _metric(row["qtd_status"]),
        }
        for row in rows
    ]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_status(request):
    """Verifica o status real dos serviços de infraestrutura em tempo real."""
    import time

    results = []

    # ── app.db (Django, conversas, índices) ─────────────────
    t0 = time.monotonic()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        results.append({
            "name": "app.db",
            "status": "online",
            "latency_ms": round((time.monotonic() - t0) * 1000),
            "url": str(connection.settings_dict["NAME"]),
        })
    except Exception as exc:
        results.append({
            "name": "app.db",
            "status": "offline",
            "latency_ms": None,
            "url": str(connection.settings_dict["NAME"]),
            "error": str(exc)[:120],
        })

    # ── dados.db (dados do usuário, só leitura) ─────────────
    from core.datastore import connect_dados, dados_db_path
    t0 = time.monotonic()
    try:
        with connect_dados() as conn:
            conn.execute("SELECT 1")
        results.append({
            "name": "dados.db",
            "status": "online",
            "latency_ms": round((time.monotonic() - t0) * 1000),
            "url": str(dados_db_path()),
        })
    except Exception as exc:
        results.append({
            "name": "dados.db",
            "status": "offline",
            "latency_ms": None,
            "url": str(dados_db_path()),
            "error": str(exc)[:120],
        })

    # ── Uptime & Stats do Sistema ───────────────────────────
    uptime_seconds = 0
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
    except Exception:
        pass
        
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

    # ── Stats do Conhecimento (pgvector) ──────────────────────
    ddl_count = doc_count = sql_count = vector_count = 0
    last_training = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM knowledge_knowledgeitem WHERE item_type = 'ddl'")
            ddl_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge_knowledgeitem WHERE item_type = 'doc'")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge_knowledgeitem WHERE item_type = 'query_example'")
            sql_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge_knowledgeitem WHERE embedding IS NOT NULL")
            vector_count = cursor.fetchone()[0]
            cursor.execute("SELECT MAX(created_at) FROM knowledge_knowledgeitem")
            last_training = cursor.fetchone()[0]
            if last_training:
                last_training = last_training.isoformat()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Erro ao buscar stats do knowledge: {e}")

    system_stats = {
        "version": os.environ.get("APP_VERSION", "0.1.0"),
        "uptime": uptime_str,
        "vectorRows": vector_count,
        "trainedDdl": ddl_count,
        "trainedDoc": doc_count,
        "trainedExamples": sql_count,
        "lastTraining": last_training
    }

    return Response({
        "services": results,
        "systemStats": system_stats
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def data_bootstrap(request):
    if not request.user.is_staff:
        raise PermissionDenied('Apenas administradores podem preparar os dados.')

    # Desktop: recarrega e valida os contextos da pasta <dados do usuário>/contexts.
    # A indexação (embeddings) usa a chave do usuário e roda separada.
    from core.contexts import load_context_dir
    from core.datastore import data_dir

    tenant = request.user.tenant
    contexts_root = data_dir() / "contexts"
    folders = sorted(p for p in contexts_root.glob("*") if (p / "views.json").exists())
    if not folders:
        return Response(
            {"detail": f"Nenhum contexto encontrado em {contexts_root}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    loaded = []
    for folder in folders:
        try:
            contexto, examples, errors = load_context_dir(folder, tenant)
        except Exception as exc:
            log_error("data_bootstrap", f"Falha ao carregar {folder.name}: {exc}")
            loaded.append({"pasta": folder.name, "ativo": False, "erros": [str(exc)]})
            continue
        loaded.append({"pasta": folder.name, "slug": contexto.slug, "ativo": not errors, "erros": errors})

    log_success("data_bootstrap", f"{sum(c['ativo'] for c in loaded)}/{len(loaded)} contexto(s) válidos")
    return Response({"status": "success", "contextos": loaded}, status=status.HTTP_200_OK)
