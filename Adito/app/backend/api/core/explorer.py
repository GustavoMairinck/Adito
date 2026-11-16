"""Catálogo e consultas locais das relações expostas pelos contextos do Adito."""
import logging
import re
import sqlite3
from contextlib import closing

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .contexts import visible_columns
from .datastore import connect_dados
from .models import Contexto

logger = logging.getLogger(__name__)


class CatalogParams(serializers.Serializer):
    contexto_id = serializers.UUIDField()


class RowsParams(CatalogParams):
    table = serializers.CharField(max_length=255)
    search = serializers.CharField(required=False, allow_blank=True, max_length=200, default='')
    filter_column = serializers.CharField(required=False, allow_blank=True, default='')
    filter_value = serializers.CharField(required=False, allow_blank=True, max_length=200, default='')
    sort = serializers.CharField(required=False, allow_blank=True, default='')
    direction = serializers.ChoiceField(choices=['asc', 'desc'], default='asc')
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.ChoiceField(choices=[25, 50, 100], default=25)
    group_by = serializers.CharField(required=False, allow_blank=True, default='')


def _contexto(request, params):
    return get_object_or_404(
        Contexto, id=params['contexto_id'], tenant=request.user.tenant, is_active=True,
    )


def _quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def _kind(view):
    if view.get('kind') in {'fact', 'dimension', 'entity'}:
        return view['kind']
    name = re.sub(r'^(?:vw_|v_)', '', view['name'].lower())
    if name.startswith(('fact', 'fato')):
        return 'fact'
    if name.startswith(('dim_', 'dimensao_')):
        return 'dimension'
    return 'entity'


def _unavailable():
    return Response(
        {'detail': 'Não foi possível ler os dados. Verifique o dados.db e recarregue os contextos em Administração.'},
        status=503,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tables(request):
    serializer = CatalogParams(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    contexto = _contexto(request, serializer.validated_data)
    catalog = []
    try:
        for view in contexto.views:
            columns = visible_columns(contexto, view['name'])
            catalog.append({
                'name': view['name'],
                'label': view.get('label') or view['name'],
                'description': view.get('description', ''),
                'kind': _kind(view),
                'columns': [{'name': name, 'type': kind} for name, kind in columns],
                'available': bool(columns),
            })
    except (FileNotFoundError, sqlite3.Error):
        logger.exception('Falha ao ler o catálogo do contexto %s', contexto.id)
        return _unavailable()
    return Response({'tables': catalog})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rows(request):
    serializer = RowsParams(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data
    contexto = _contexto(request, params)
    view = contexto.view_config(params['table'])
    if view is None:
        return Response({'detail': 'Tabela indisponível neste contexto.'}, status=404)

    try:
        columns = [name for name, _ in visible_columns(contexto, view['name'])]
        if not columns:
            return Response({'detail': 'Esta tabela não possui colunas disponíveis para consulta.'}, status=400)
        for key in ('sort', 'filter_column', 'group_by'):
            if params[key] and params[key] not in columns:
                raise serializers.ValidationError({key: 'Selecione uma coluna disponível.'})
        if params['filter_value'] and not params['filter_column']:
            raise serializers.ValidationError({'filter_column': 'Selecione a coluna do filtro.'})

        clauses, values = [], []
        if params['search']:
            # A busca trata %, _ e ! como texto literal.
            search = params['search'].replace('!', '!!').replace('%', '!%').replace('_', '!_')
            clauses.append('(' + ' OR '.join(
                f"CAST({_quote(column)} AS TEXT) LIKE ? ESCAPE '!'" for column in columns
            ) + ')')
            values.extend([f'%{search}%'] * len(columns))
        if params['filter_column'] and params['filter_value']:
            clauses.append(f'CAST({_quote(params["filter_column"])} AS TEXT) = ?')
            values.append(params['filter_value'])

        source = _quote(view['name'])
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        sort = params['sort'] or columns[0]
        order = ', '.join([
            f'{_quote(sort)} {params["direction"].upper()}',
            *[_quote(column) for column in columns if column != sort],
        ])
        page_size = int(params['page_size'])
        # O SQL usa apenas a relação e as colunas já validadas no contexto.
        # Os valores fornecidos pelo usuário são parâmetros da consulta.
        with closing(connect_dados()) as conn:
            conn.execute('BEGIN')
            total = conn.execute(f'SELECT COUNT(*) FROM {source}{where}', values).fetchone()[0]
            page = min(params['page'], max(1, (total + page_size - 1) // page_size))
            records = conn.execute(
                f'SELECT {", ".join(map(_quote, columns))} FROM {source}{where} '
                f'ORDER BY {order} LIMIT ? OFFSET ?',
                [*values, page_size, (page - 1) * page_size],
            ).fetchall()
            distribution = []
            if params['group_by']:
                group = _quote(params['group_by'])
                distribution = [_record(row) for row in conn.execute(
                    f'SELECT {group} AS value, COUNT(*) AS count FROM {source}{where} '
                    f'GROUP BY {group} ORDER BY COUNT(*) DESC, {group} LIMIT 12', values,
                )]
        return Response({
            'rows': [_record(record) for record in records],
            'total': total, 'page': page, 'page_size': page_size,
            'distribution': distribution,
        })
    except (FileNotFoundError, sqlite3.Error):
        logger.exception('Falha ao consultar a relação %s do contexto %s', view['name'], contexto.id)
        return _unavailable()


def _record(row):
    return {
        key: '0x' + value.hex() if isinstance(value, bytes) else value
        for key, value in dict(row).items()
    }
