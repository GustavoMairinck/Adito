from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
from django.test import TestCase
from rest_framework.test import APIClient

from agents.bi_agent.agent import BIAgent
from agents.bi_agent.sql_security import validate_read_only_sql
from analytics_index.services import fetch_distinct_candidates
from core.contexts import describe_views, load_context_dir, view_columns
from core.datastore import ReadPolicy, connect_dados
from core.models import Contexto, Tenant, User

RAIZ_REPO = Path(__file__).resolve().parents[5]
SCRIPTS_DIR = RAIZ_REPO / "Adito" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from gerar_duckdb import (  # noqa: E402
    CONTAGENS_ESPERADAS_FATOS,
    PROPOSTA_PADRAO,
    SAIDA_DUCKDB_PADRAO,
    extrair_fatos_proposta,
    gerar_banco_duckdb,
    mapear_tipo_duckdb,
)

FATOS_NOMES = frozenset(CONTAGENS_ESPERADAS_FATOS.keys())


def _criar_duckdb_sintetico(caminho_duckdb: Path) -> None:
    """Cria um arquivo `.duckdb` mínimo contendo as 6 tabelas fato com as colunas do contexto."""
    spec = json.loads(
        (RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes" / "views.json").read_text(
            encoding="utf-8"
        )
    )
    conn = duckdb.connect(str(caminho_duckdb))
    try:
        for view in spec["views"]:
            name = view["name"]
            cols = sorted(
                set(view.get("embed_columns", []))
                | set(view.get("local_search_columns", []))
                | set(view.get("sensitive_columns", []))
                | {"id", "ano"}
            )
            col_defs = ", ".join(
                f'"{c}" INTEGER' if c in ("id", "ano") else f'"{c}" VARCHAR'
                for c in cols
            )
            conn.execute(f'CREATE TABLE main."{name}" ({col_defs})')
            vals = ", ".join("1" if c == "id" else ("2024" if c == "ano" else f"'val_{c}'") for c in cols)
            conn.execute(f'INSERT INTO main."{name}" VALUES ({vals})')
    finally:
        conn.close()


class DuckDBSecurityAndContextTests(TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.synthetic_duckdb = Path(self.tmpdir.name) / "test_dados.duckdb"
        _criar_duckdb_sintetico(self.synthetic_duckdb)
        self.tenant = Tenant.objects.create(name="ifes-test")

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_mapear_tipo_duckdb_e_extrair_fatos_proposta(self) -> None:
        self.assertEqual(mapear_tipo_duckdb("bigint"), "BIGINT")
        self.assertEqual(mapear_tipo_duckdb("integer"), "INTEGER")
        self.assertEqual(mapear_tipo_duckdb("numeric(12,2)"), "DECIMAL(12,2)")
        self.assertEqual(mapear_tipo_duckdb("boolean"), "BOOLEAN")
        self.assertEqual(mapear_tipo_duckdb("date"), "DATE")
        self.assertEqual(mapear_tipo_duckdb("tipo_modalidade"), "VARCHAR")

        fatos = extrair_fatos_proposta(PROPOSTA_PADRAO)
        self.assertEqual(len(fatos), 6)
        self.assertEqual({nome for nome, _ in fatos}, FATOS_NOMES)

    def test_validate_read_only_sql_duckdb_permite_consultas_olap_validas(self) -> None:
        queries = [
            "SELECT campus, COUNT(*) AS total FROM vfact_extensao_acao_resolved WHERE campus ILIKE '%Serra%' GROUP BY campus",
            "SELECT EXTRACT(YEAR FROM data_inicio)::INTEGER AS ano, COUNT(DISTINCT id_projeto) FROM vfact_projeto_pesquisa_resolved GROUP BY 1",
            "WITH resumo AS (SELECT ano, SUM(investimento_total_estimado) AS total FROM vfact_orientacao_bolsa_resolved GROUP BY ano) SELECT ano, total FROM resumo ORDER BY ano DESC LIMIT 5",
        ]
        for sql in queries:
            ok, err = validate_read_only_sql(sql, FATOS_NOMES, dialect="duckdb")
            self.assertTrue(ok, f"Deveria aprovar SQL válido '{sql}', mas falhou com: {err}")

    def test_validate_read_only_sql_duckdb_bloqueia_escrita_arquivos_e_colunas_sensiveis(self) -> None:
        bloqueadas = [
            "DROP TABLE vfact_extensao_acao_resolved",
            "COPY vfact_extensao_acao_resolved TO '/tmp/out.csv'",
            "ATTACH '/tmp/outro.db' AS outro",
            "INSTALL httpfs",
            "LOAD httpfs",
            "PRAGMA database_list",
            "SET enable_external_access = true",
            "SELECT * FROM read_csv_auto('/etc/passwd')",
            "SELECT * FROM read_parquet('/tmp/test.parquet')",
            "SELECT * FROM read_json('/tmp/test.json')",
            "SELECT nome FROM pessoa",
            "SELECT campus FROM unificado.vfact_extensao_acao_resolved",
            "SELECT coordenador_cpf FROM vfact_extensao_acao_resolved",
            "SELECT email_participante FROM vfact_extensao_participacao_resolved",
        ]
        for sql in bloqueadas:
            ok, err = validate_read_only_sql(sql, FATOS_NOMES, dialect="duckdb")
            self.assertFalse(ok, f"Deveria bloquear SQL inseguro: {sql}")
            self.assertIsNotNone(err)

        # Verifica bloqueio de sensitive_columns declaradas no contexto e de SELECT *
        sens = {("vfact_extensao_acao_resolved", "documento_secreto")}
        ok_col, _ = validate_read_only_sql(
            "SELECT documento_secreto FROM vfact_extensao_acao_resolved",
            FATOS_NOMES,
            dialect="duckdb",
            sensitive_columns=sens,
        )
        self.assertFalse(ok_col)

        ok_star, _ = validate_read_only_sql(
            "SELECT * FROM vfact_extensao_acao_resolved",
            FATOS_NOMES,
            dialect="duckdb",
            sensitive_columns=sens,
        )
        self.assertFalse(ok_star)

        ok_count_star, err_count = validate_read_only_sql(
            "SELECT COUNT(*) AS total FROM vfact_extensao_acao_resolved",
            FATOS_NOMES,
            dialect="duckdb",
            sensitive_columns=sens,
        )
        self.assertTrue(ok_count_star, err_count)

    def test_connect_dados_e_read_policy_no_duckdb(self) -> None:
        policy = ReadPolicy(
            exposed_views=frozenset({"vfact_extensao_acao_resolved"}),
            sensitive_columns=frozenset({("vfact_extensao_acao_resolved", "orgao_fomento")}),
        )
        with connect_dados(policy=policy, path=self.synthetic_duckdb) as conn:
            row = conn.execute(
                "SELECT id, campus FROM vfact_extensao_acao_resolved"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 1)
            self.assertEqual(row["campus"], "val_campus")
            self.assertEqual(dict(row), {"id": 1, "campus": "val_campus"})

            with self.assertRaises(PermissionError):
                conn.execute("SELECT orgao_fomento FROM vfact_extensao_acao_resolved")

            with self.assertRaises(PermissionError):
                conn.execute("SELECT id FROM vfact_projeto_pesquisa_resolved")

    def test_connect_dados_bloqueia_acesso_externo_e_reconfiguracao_no_banco(self) -> None:
        """Verifica a proteção em nível de banco (DuckDB config), mesmo sem ReadPolicy (segunda camada)."""
        with connect_dados(path=self.synthetic_duckdb) as conn:
            with self.assertRaises(duckdb.PermissionException):
                conn.execute("SELECT * FROM '/tmp/qualquer_arquivo.csv'")

            with self.assertRaises(duckdb.InvalidInputException):
                conn.execute("SET enable_external_access = true")

    def test_load_context_dir_ativa_pesquisa_extensao_e_desativa_exemplo_vendas(self) -> None:
        pasta_ifes = RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes"
        pasta_vendas = RAIZ_REPO / "Adito" / "app" / "contexts" / "exemplo-vendas"

        ctx_ifes, examples_ifes, errors_ifes = load_context_dir(
            pasta_ifes, self.tenant, dados_path=self.synthetic_duckdb
        )
        self.assertEqual(errors_ifes, [])
        self.assertTrue(ctx_ifes.is_active)
        self.assertEqual(len(ctx_ifes.views), 6)
        self.assertGreaterEqual(len(examples_ifes), 6)

        ddl = describe_views(ctx_ifes, dados_path=self.synthetic_duckdb)
        for view_name in FATOS_NOMES:
            self.assertIn(view_name, ddl)

        ctx_vendas, _, errors_vendas = load_context_dir(
            pasta_vendas, self.tenant, dados_path=self.synthetic_duckdb
        )
        self.assertEqual(errors_vendas, [])
        self.assertFalse(ctx_vendas.is_active)

    def test_bi_agent_execute_query_e_fetch_distinct_candidates(self) -> None:
        pasta_ifes = RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes"
        ctx_ifes, _, _ = load_context_dir(
            pasta_ifes, self.tenant, dados_path=self.synthetic_duckdb
        )
        agent = BIAgent(
            llm_model=MagicMock(),
            embedder=MagicMock(),
            dados_path=str(self.synthetic_duckdb),
        )
        rows = agent.execute_query(
            "SELECT campus, COUNT(*) AS total FROM vfact_extensao_acao_resolved GROUP BY campus",
            contexto_id=str(ctx_ifes.id),
        )
        self.assertEqual(rows, [{"campus": "val_campus", "total": 1}])

        cols = view_columns("vfact_extensao_acao_resolved", dados_path=self.synthetic_duckdb)
        self.assertTrue(any(c[0] == "campus" for c in cols))

        import os

        old_env = os.environ.get("ORACULO_DADOS_DB")
        os.environ["ORACULO_DADOS_DB"] = str(self.synthetic_duckdb)
        try:
            candidates = fetch_distinct_candidates(ctx_ifes, "vfact_extensao_acao_resolved")
            self.assertEqual(len(candidates), 1)
        finally:
            if old_env is None:
                os.environ.pop("ORACULO_DADOS_DB", None)
            else:
                os.environ["ORACULO_DADOS_DB"] = old_env

    def test_banco_duckdb_real_contagens_fatos_quando_presente(self) -> None:
        if not SAIDA_DUCKDB_PADRAO.exists():
            self.skipTest("dados.duckdb real não está gerado no ambiente atual.")
        with connect_dados(path=SAIDA_DUCKDB_PADRAO) as conn:
            for nome_fato, esperado in CONTAGENS_ESPERADAS_FATOS.items():
                obtido = conn.execute(f'SELECT COUNT(*) FROM "{nome_fato}"').fetchone()[0]
                self.assertEqual(obtido, esperado, f"Contagem divergente em {nome_fato}")

    def test_gemini_config_e_llm_configured(self) -> None:
        import os
        from agents.config import get_chat_llm, get_embeddings, get_gemini_api_key
        from core.views import llm_configured

        old_gemini = os.environ.pop("GEMINI_API_KEY", None)
        old_google = os.environ.pop("GOOGLE_API_KEY", None)
        try:
            self.assertFalse(llm_configured())
            os.environ["GEMINI_API_KEY"] = "test-gemini-key-123"
            self.assertTrue(llm_configured())
            self.assertEqual(get_gemini_api_key(), "test-gemini-key-123")
            llm = get_chat_llm(temperature=0.0)
            emb = get_embeddings()
            self.assertIsNotNone(llm)
            self.assertIsNotNone(emb)
        finally:
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            if old_gemini is not None:
                os.environ["GEMINI_API_KEY"] = old_gemini
            if old_google is not None:
                os.environ["GOOGLE_API_KEY"] = old_google

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
        self.db_path = Path(self.folder.name) / 'dados.duckdb'
        self.env = patch.dict(os.environ, {'ORACULO_DADOS_DB': str(self.db_path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        conn = duckdb.connect(str(self.db_path))
        try:
            conn.execute('''
                CREATE TABLE area (id INTEGER PRIMARY KEY, nome VARCHAR);
                INSERT INTO area VALUES (1, 'Computação'), (2, 'Educação');
                CREATE TABLE projeto (id INTEGER PRIMARY KEY, titulo VARCHAR, id_area INTEGER, ano INTEGER, cpf VARCHAR);
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
        finally:
            conn.close()
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
        conn = duckdb.connect(str(self.db_path))
        try:
            conn.execute('CREATE TABLE dim_nullable (codigo INTEGER, arquivo BLOB)')
            conn.executemany('INSERT INTO dim_nullable VALUES (?, ?)', [(None, b'\xff'), (0, b'')])
        finally:
            conn.close()
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
        conn = duckdb.connect(str(self.db_path))
        try:
            conn.execute('DROP VIEW v_fato_projeto')
        finally:
            conn.close()
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
