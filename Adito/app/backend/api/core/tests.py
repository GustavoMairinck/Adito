import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Contexto, Tenant, User


class ExplorerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Campus Serra')
        cls.user = User.objects.create_user(username='teste', tenant=cls.tenant)
        cls.contexto = Contexto.objects.create(
            tenant=cls.tenant, slug='unificado', name='Modelo unificado',
            views=[
                {'name': 'v_fato_projeto', 'sensitive_columns': ['cpf']},
                {'name': 'dim_area'},
                {'name': 'iniciativa', 'label': 'Iniciativas'},
                {'name': 'projetos_pesquisa', 'kind': 'fact', 'label': 'Projetos de pesquisa'},
            ],
        )
        cls.foreign = Contexto.objects.create(
            tenant=Tenant.objects.create(name='Outro campus'), slug='outro', name='Outro contexto',
        )

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db_path = Path(self.folder.name) / 'dados.db'
        self.env = patch.dict(os.environ, {'ORACULO_DADOS_DB': str(self.db_path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE area (id INTEGER PRIMARY KEY, nome TEXT);
                INSERT INTO area VALUES (1, 'Computação'), (2, 'Educação');
                CREATE TABLE projeto (id INTEGER PRIMARY KEY, titulo TEXT, id_area INTEGER, ano INTEGER, cpf TEXT);
                CREATE VIEW v_fato_projeto AS
                    SELECT p.id, p.titulo, a.nome AS area, p.ano, p.cpf
                    FROM projeto p JOIN area a ON a.id = p.id_area;
                CREATE VIEW dim_area AS SELECT * FROM area;
                CREATE VIEW iniciativa AS SELECT id, titulo FROM projeto;
                CREATE VIEW projetos_pesquisa AS SELECT id, titulo FROM projeto;
            ''')
            conn.executemany('INSERT INTO projeto VALUES (?, ?, ?, ?, ?)', [
                (i, 'Projeto 100%_IFES' if i == 1 else f'Projeto {i}', 1 + i % 2, 2025 + i % 2, 'restrito')
                for i in range(1, 34)
            ])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def catalog(self, **params):
        return self.client.get('/api/explorer/tables', {'contexto_id': str(self.contexto.id), **params})

    def rows(self, **params):
        return self.client.get('/api/explorer/rows', {
            'contexto_id': str(self.contexto.id), 'table': 'v_fato_projeto', **params,
        })

    def test_catalog_uses_context_metadata_and_hides_sensitive_columns(self):
        response = self.catalog()
        self.assertEqual(response.status_code, 200)
        tables = response.data['tables']
        self.assertEqual([table['kind'] for table in tables], ['fact', 'dimension', 'entity', 'fact'])
        self.assertEqual(tables[2]['label'], 'Iniciativas')
        self.assertNotIn('cpf', [column['name'] for column in tables[0]['columns']])

    def test_paginated_rows_sorting_and_last_page(self):
        first = self.rows()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['total'], 33)
        self.assertEqual(len(first.data['rows']), 25)
        self.assertEqual(first.data['rows'][0]['id'], 1)
        self.assertNotIn('cpf', first.data['rows'][0])
        last = self.rows(page=999, sort='id', direction='desc')
        self.assertEqual(last.data['page'], 2)
        self.assertEqual(len(last.data['rows']), 8)
        self.assertEqual(last.data['rows'][-1]['id'], 1)

    def test_search_escapes_wildcards_and_sql_is_parameterized(self):
        self.assertEqual(self.rows(search='100%_').data['total'], 1)
        self.assertEqual(self.rows(search="' OR 1=1 --").data['total'], 0)
        self.assertEqual(self.rows(search='restrito').data['total'], 0)

    def test_filters_and_distribution_use_all_matching_rows(self):
        response = self.rows(filter_column='ano', filter_value='2026', group_by='area')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 17)
        self.assertEqual(response.data['distribution'], [{'value': 'Educação', 'count': 17}])
        all_rows = self.rows(group_by='area')
        self.assertEqual(sum(item['count'] for item in all_rows.data['distribution']), 33)

    def test_dimensions_entities_and_empty_results(self):
        self.assertEqual(self.rows(table='dim_area').data['total'], 2)
        self.assertEqual(self.rows(table='iniciativa').data['total'], 33)
        empty = self.rows(search='inexistente')
        self.assertEqual(empty.data['rows'], [])
        self.assertEqual(empty.data['total'], 0)
        self.assertEqual(empty.data['page'], 1)

    def test_null_and_binary_values_and_relations_with_only_sensitive_columns(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('CREATE TABLE dim_nullable (codigo INTEGER, arquivo BLOB)')
            conn.executemany('INSERT INTO dim_nullable VALUES (?, ?)', [(None, b'\xff'), (0, b'')])
        self.contexto.views.append({'name': 'dim_nullable'})
        self.contexto.views[2]['sensitive_columns'] = ['id', 'titulo']
        self.contexto.save(update_fields=['views'])
        response = self.rows(table='dim_nullable', group_by='codigo')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)
        self.assertIsNone(response.data['rows'][0]['codigo'])
        self.assertEqual(response.data['rows'][0]['arquivo'], '0xff')
        self.assertFalse(self.catalog().data['tables'][2]['available'])
        self.assertEqual(self.rows(table='iniciativa').status_code, 400)

    def test_rejects_unexposed_tables_sensitive_columns_and_invalid_parameters(self):
        self.assertEqual(self.rows(table='projeto').status_code, 404)
        self.assertEqual(self.rows(table='projeto; DROP TABLE area').status_code, 404)
        for params in [
            {'sort': 'cpf'}, {'filter_column': 'cpf', 'filter_value': 'restrito'},
            {'group_by': 'cpf'}, {'sort': 'id DESC; DROP TABLE area'},
            {'page': 0}, {'page_size': 1000}, {'direction': 'invalido'},
            {'contexto_id': 'invalido'}, {'filter_value': '2026'},
        ]:
            with self.subTest(params=params):
                self.assertEqual(self.rows(**params).status_code, 400)

    def test_requires_authentication_and_an_active_context_from_same_tenant(self):
        self.assertEqual(self.catalog(contexto_id=str(self.foreign.id)).status_code, 404)
        self.assertEqual(self.rows(contexto_id=str(self.foreign.id)).status_code, 404)
        self.contexto.is_active = False
        self.contexto.save(update_fields=['is_active'])
        self.assertEqual(self.catalog().status_code, 404)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.catalog().status_code, 401)
        self.assertEqual(self.rows().status_code, 401)

    def test_desktop_token_allows_exploration_without_a_gemini_key(self):
        self.client.force_authenticate(user=None)
        with patch.dict(os.environ, {
            'ORACULO_LOCAL_TOKEN': 'token-do-desktop',
            'DEFAULT_TENANT_NAME': self.tenant.name,
            'GEMINI_API_KEY': '',
        }):
            headers = {'HTTP_X_ORACULO_TOKEN': 'token-do-desktop'}
            params = {'contexto_id': str(self.contexto.id)}
            self.assertEqual(self.client.get('/api/explorer/tables', params, **headers).status_code, 200)
            response = self.client.get('/api/explorer/rows', {
                **params, 'table': 'v_fato_projeto',
            }, **headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['total'], 33)

    def test_missing_database_and_stale_context_return_actionable_errors(self):
        with self.assertLogs('core.explorer', level='ERROR'), patch.dict(
            os.environ, {'ORACULO_DADOS_DB': str(self.db_path) + '.missing'},
        ):
            self.assertEqual(self.catalog().status_code, 503)
            self.assertEqual(self.rows().status_code, 503)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DROP VIEW v_fato_projeto')
        self.assertFalse(self.catalog().data['tables'][0]['available'])
        self.assertEqual(self.rows().status_code, 400)

    def test_gemini_key_validation_uses_google_header_and_configured_model(self):
        from agents.config import GEMINI_MODEL
        with patch('core.views.httpx.get') as get:
            get.return_value.status_code = 200
            response = self.client.post('/api/config/test-llm-key', {'key': 'test-key'})
        self.assertTrue(response.data['ok'])
        self.assertEqual(get.call_args.args[0],
                         f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}')
        self.assertEqual(get.call_args.kwargs['headers'], {'x-goog-api-key': 'test-key'})

    def test_gemini_key_validation_reports_unavailable_model(self):
        with patch('core.views.httpx.get') as get:
            get.return_value.status_code = 404
            response = self.client.post('/api/config/test-llm-key', {'key': 'test-key'})
        self.assertFalse(response.data['ok'])
        self.assertIn('GEMINI_MODEL', response.data['reason'])
