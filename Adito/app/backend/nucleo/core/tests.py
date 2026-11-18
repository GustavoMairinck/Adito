"""Testes do núcleo (sem Django): rodar de backend/nucleo com `python -m unittest core.tests`."""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.bi_agent.agent import BIAgent
from agents.bi_agent.sql_security import validate_read_only_sql
from analytics_index.services import fetch_distinct_candidates
from core import db
from core.contexts import describe_views, load_context_dir, view_columns
from core.datastore import (
    DEFAULT_REPO_SQLITE,
    ReadPolicy,
    close_dados,
    connect_dados,
)
from core.records import Contexto, Tenant, get_local_user
from core.schema import ensure_schema
from rpc import session
from rpc.errors import ApiError
from rpc.registry import dispatch, load_handlers

RAIZ_REPO = Path(__file__).resolve().parents[5]

FATOS_NOMES = frozenset({
    "vfact_extensao_acao_resolved",
    "vfact_extensao_participacao_resolved",
    "vfact_projeto_pesquisa_resolved",
    "vfact_orientacao_bolsa_resolved",
    "vfact_producao_cientifica_resolved",
    "vfact_grupo_pesquisa_membro_resolved",
})


def _criar_sqlite_sintetico(caminho_sqlite: Path) -> None:
    """Cria um arquivo `.db` mínimo contendo as 6 tabelas fato com as colunas do contexto."""
    spec = json.loads(
        (RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes" / "views.json").read_text(
            encoding="utf-8"
        )
    )
    conn = sqlite3.connect(str(caminho_sqlite))
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
                f'"{c}" INTEGER' if c in ("id", "ano") else f'"{c}" TEXT'
                for c in cols
            )
            conn.execute(f'CREATE TABLE "{name}" ({col_defs})')
            vals = ", ".join("1" if c == "id" else ("2024" if c == "ano" else f"'val_{c}'") for c in cols)
            conn.execute(f'INSERT INTO "{name}" VALUES ({vals})')
        conn.commit()
    finally:
        conn.close()


class AppDbTestCase(unittest.TestCase):
    """Cada teste usa um app.db novo numa pasta temporária (o TestCase do Django fazia rollback)."""

    def setUp(self) -> None:
        self.appdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.appdir.cleanup)
        env = patch.dict(os.environ, {"ORACULO_APP_DB": str(Path(self.appdir.name) / "app.db")})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(db.close)
        self.addCleanup(close_dados)
        ensure_schema()
        session.reset()
        self.addCleanup(session.reset)


def call(method: str, params: dict | None = None) -> tuple[int, object]:
    """Chama um método do núcleo e devolve (status, corpo), como o front recebe."""
    load_handlers()
    try:
        return 200, asyncio.run(dispatch(method, params or {}))
    except ApiError as exc:
        return exc.status, exc.data


class SQLiteSecurityAndContextTests(AppDbTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.synthetic_sqlite = Path(self.tmpdir.name) / "test_dados.db"
        _criar_sqlite_sintetico(self.synthetic_sqlite)
        self.tenant = Tenant(name="ifes-test").insert()

    def test_fatos_nomes_cobertura_completa(self) -> None:
        self.assertEqual(len(FATOS_NOMES), 6)
        spec = json.loads(
            (RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes" / "views.json").read_text(
                encoding="utf-8"
            )
        )
        spec_views = {v["name"] for v in spec["views"]}
        self.assertEqual(spec_views, FATOS_NOMES)

    def test_validate_read_only_sql_permite_consultas_validas(self) -> None:
        queries = [
            "SELECT campus, COUNT(*) AS total FROM vfact_extensao_acao_resolved WHERE campus LIKE '%Serra%' GROUP BY campus",
            "SELECT ano_inicio AS ano, COUNT(DISTINCT id_projeto) FROM vfact_projeto_pesquisa_resolved GROUP BY ano_inicio",
            "WITH resumo AS (SELECT ano, SUM(investimento_total_estimado) AS total FROM vfact_orientacao_bolsa_resolved GROUP BY ano) SELECT ano, total FROM resumo ORDER BY ano DESC LIMIT 5",
        ]
        for sql in queries:
            ok, err = validate_read_only_sql(sql, FATOS_NOMES, dialect="sqlite")
            self.assertTrue(ok, f"Deveria aprovar SQL válido '{sql}', mas falhou com: {err}")

    def test_validate_read_only_sql_bloqueia_escrita_e_colunas_sensiveis(self) -> None:
        bloqueadas = [
            "DROP TABLE vfact_extensao_acao_resolved",
            "ATTACH '/tmp/outro.db' AS outro",
            "SELECT nome FROM pessoa",
            "SELECT coordenador_cpf FROM vfact_extensao_acao_resolved",
            "SELECT email_participante FROM vfact_extensao_participacao_resolved",
        ]
        for sql in bloqueadas:
            ok, err = validate_read_only_sql(sql, FATOS_NOMES, dialect="sqlite")
            self.assertFalse(ok, f"Deveria bloquear SQL inseguro: {sql}")
            self.assertIsNotNone(err)

        # Bloqueio incondicional de SELECT * mesmo sem sensitive_columns declaradas
        for star_sql in (
            "SELECT * FROM vfact_extensao_acao_resolved",
            "SELECT a.* FROM vfact_extensao_acao_resolved AS a",
        ):
            ok_star_sem_sens, err_star = validate_read_only_sql(
                star_sql, FATOS_NOMES, dialect="sqlite", sensitive_columns=None
            )
            self.assertFalse(ok_star_sem_sens, f"Deveria bloquear '{star_sql}' mesmo sem sensitive_columns")
            self.assertIsNotNone(err_star)

        # Verifica bloqueio de sensitive_columns declaradas no contexto
        sens = {("vfact_extensao_acao_resolved", "documento_secreto")}
        ok_col, _ = validate_read_only_sql(
            "SELECT documento_secreto FROM vfact_extensao_acao_resolved",
            FATOS_NOMES,
            dialect="sqlite",
            sensitive_columns=sens,
        )
        self.assertFalse(ok_col)

        ok_count_star, err_count = validate_read_only_sql(
            "SELECT COUNT(*) AS total FROM vfact_extensao_acao_resolved",
            FATOS_NOMES,
            dialect="sqlite",
            sensitive_columns=sens,
        )
        self.assertTrue(ok_count_star, err_count)

    def test_connect_dados_e_read_policy_no_sqlite(self) -> None:
        policy = ReadPolicy(
            exposed_views=frozenset({"vfact_extensao_acao_resolved"}),
            sensitive_columns=frozenset({("vfact_extensao_acao_resolved", "orgao_fomento")}),
        )
        with connect_dados(policy=policy, path=self.synthetic_sqlite) as conn:
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

    def test_connect_dados_bloqueia_mutacoes_e_authorizer_no_banco(self) -> None:
        """Verifica a proteção em nível de driver SQLite (set_authorizer e query_only)."""
        with connect_dados(path=self.synthetic_sqlite) as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("INSERT INTO vfact_extensao_acao_resolved (id) VALUES (99)")

            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("DROP TABLE vfact_extensao_acao_resolved")

            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("ATTACH DATABASE '/tmp/outro.db' AS outro")

    def test_load_context_dir_ativa_pesquisa_extensao_e_desativa_exemplo_vendas(self) -> None:
        pasta_ifes = RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes"
        pasta_vendas = RAIZ_REPO / "Adito" / "app" / "contexts" / "exemplo-vendas"

        ctx_ifes, examples_ifes, errors_ifes = load_context_dir(
            pasta_ifes, self.tenant, dados_path=self.synthetic_sqlite
        )
        self.assertEqual(errors_ifes, [])
        self.assertTrue(ctx_ifes.is_active)
        self.assertEqual(len(ctx_ifes.views), 6)
        self.assertGreaterEqual(len(examples_ifes), 6)

        ddl = describe_views(ctx_ifes, dados_path=self.synthetic_sqlite)
        for view_name in FATOS_NOMES:
            self.assertIn(view_name, ddl)

        ctx_vendas, _, errors_vendas = load_context_dir(
            pasta_vendas, self.tenant, dados_path=self.synthetic_sqlite
        )
        self.assertEqual(errors_vendas, [])
        self.assertFalse(ctx_vendas.is_active)

    def test_bi_agent_execute_query_e_fetch_distinct_candidates(self) -> None:
        pasta_ifes = RAIZ_REPO / "Adito" / "app" / "contexts" / "pesquisa-extensao-ifes"
        ctx_ifes, _, _ = load_context_dir(
            pasta_ifes, self.tenant, dados_path=self.synthetic_sqlite
        )
        agent = BIAgent(
            llm_model=MagicMock(),
            embedder=MagicMock(),
            dados_path=str(self.synthetic_sqlite),
        )
        rows = agent.execute_query(
            "SELECT campus, COUNT(*) AS total FROM vfact_extensao_acao_resolved GROUP BY campus",
            contexto_id=str(ctx_ifes.id),
        )
        self.assertEqual(rows, [{"campus": "val_campus", "total": 1}])

        cols = view_columns("vfact_extensao_acao_resolved", dados_path=self.synthetic_sqlite)
        self.assertTrue(any(c[0] == "campus" for c in cols))

        old_env = os.environ.get("ORACULO_DADOS_DB")
        os.environ["ORACULO_DADOS_DB"] = str(self.synthetic_sqlite)
        try:
            candidates = fetch_distinct_candidates(ctx_ifes, "vfact_extensao_acao_resolved")
            self.assertEqual(len(candidates), 1)
        finally:
            if old_env is None:
                os.environ.pop("ORACULO_DADOS_DB", None)
            else:
                os.environ["ORACULO_DADOS_DB"] = old_env

    def test_banco_sqlite_real_contagens_fatos_quando_presente(self) -> None:
        if not DEFAULT_REPO_SQLITE.exists():
            self.skipTest("dados.db real não está gerado no ambiente atual.")
        with connect_dados(path=DEFAULT_REPO_SQLITE) as conn:
            for nome_fato in FATOS_NOMES:
                obtido = conn.execute(f'SELECT COUNT(*) FROM "{nome_fato}"').fetchone()[0]
                self.assertGreater(obtido, 0, f"Contagem nula em {nome_fato}")

    def test_gemini_config_e_llm_configured(self) -> None:
        from agents.config import get_chat_llm, get_embeddings, get_gemini_api_key
        from rpc.core_methods import llm_configured

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


class Resposta:
    def __init__(self, status, data):
        self.status_code, self.data = status, data


class ExplorerTests(AppDbTestCase):
    def setUp(self):
        super().setUp()
        tenant_env = patch.dict(os.environ, {'DEFAULT_TENANT_NAME': 'Campus Serra'})
        tenant_env.start()
        self.addCleanup(tenant_env.stop)
        user = get_local_user()
        self.contexto = Contexto(
            tenant_id=user.tenant_id, slug='unificado', name='Modelo unificado',
            views=[
                {'name': 'v_fato_projeto', 'sensitive_columns': ['cpf']},
                {'name': 'dim_area'},
                {'name': 'iniciativa', 'label': 'Iniciativas'},
                {'name': 'projetos_pesquisa', 'kind': 'fact', 'label': 'Projetos de pesquisa'},
            ],
        ).insert()
        self.foreign = Contexto(
            tenant_id=Tenant(name='Outro campus').insert().id, slug='outro', name='Outro contexto',
        ).insert()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db_path = Path(self.folder.name) / 'dados.db'
        self.env = patch.dict(os.environ, {'ORACULO_DADOS_DB': str(self.db_path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        close_dados()
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute('''
                CREATE TABLE area (id INTEGER PRIMARY KEY, nome TEXT);
            ''')
            conn.execute("INSERT INTO area VALUES (1, 'Computação')")
            conn.execute("INSERT INTO area VALUES (2, 'Educação')")
            conn.execute('''
                CREATE TABLE projeto (id INTEGER PRIMARY KEY, titulo TEXT, id_area INTEGER, ano INTEGER, cpf TEXT);
            ''')
            conn.execute('''
                CREATE VIEW v_fato_projeto AS
                    SELECT p.id, p.titulo, a.nome AS area, p.ano, p.cpf
                    FROM projeto p JOIN area a ON a.id = p.id_area;
            ''')
            conn.execute("CREATE VIEW dim_area AS SELECT * FROM area;")
            conn.execute("CREATE VIEW iniciativa AS SELECT id, titulo FROM projeto;")
            conn.execute("CREATE VIEW projetos_pesquisa AS SELECT id, titulo FROM projeto;")
            conn.executemany('INSERT INTO projeto VALUES (?, ?, ?, ?, ?)', [
                (i, 'Projeto 100%_IFES' if i == 1 else f'Projeto {i}', 1 + i % 2, 2025 + i % 2, 'restrito')
                for i in range(1, 34)
            ])
            conn.commit()
        finally:
            conn.close()

    def catalog(self, **params):
        return Resposta(*call('explorer.tables', {'contexto_id': str(self.contexto.id), **params}))

    def rows(self, **params):
        return Resposta(*call('explorer.rows', {
            'contexto_id': str(self.contexto.id), 'table': 'v_fato_projeto', **params,
        }))

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
        close_dados()
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute('CREATE TABLE dim_nullable (codigo INTEGER, arquivo BLOB)')
            conn.executemany('INSERT INTO dim_nullable VALUES (?, ?)', [(None, b'\xff'), (0, b'')])
            conn.commit()
        finally:
            conn.close()
        self.contexto.views.append({'name': 'dim_nullable'})
        self.contexto.views[2]['sensitive_columns'] = ['id', 'titulo']
        self.contexto.update('views')
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

    def test_requires_an_active_context_from_same_tenant(self):
        self.assertEqual(self.catalog(contexto_id=str(self.foreign.id)).status_code, 404)
        self.assertEqual(self.rows(contexto_id=str(self.foreign.id)).status_code, 404)
        self.contexto.is_active = False
        self.contexto.update('is_active')
        self.assertEqual(self.catalog().status_code, 404)

    def test_exploration_works_without_a_gemini_key(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': '', 'GOOGLE_API_KEY': ''}):
            self.assertEqual(self.catalog().status_code, 200)
            response = self.rows()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['total'], 33)

    def test_missing_database_and_stale_context_return_actionable_errors(self):
        with self.assertLogs('rpc.explorer', level='ERROR'), patch.dict(
            os.environ, {'ORACULO_DADOS_DB': str(self.db_path) + '.missing'},
        ):
            self.assertEqual(self.catalog().status_code, 503)
            self.assertEqual(self.rows().status_code, 503)
        close_dados()
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute('DROP VIEW v_fato_projeto')
            conn.commit()
        finally:
            conn.close()
        self.assertFalse(self.catalog().data['tables'][0]['available'])
        self.assertEqual(self.rows().status_code, 400)

    def test_gemini_key_validation_uses_google_header_and_configured_model(self):
        from agents.config import GEMINI_MODEL
        with patch('rpc.core_methods.httpx.get') as get:
            get.return_value.status_code = 200
            response = Resposta(*call('config.test_llm_key', {'key': 'test-key'}))
        self.assertTrue(response.data['ok'])
        self.assertEqual(get.call_args.args[0],
                         f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}')
        self.assertEqual(get.call_args.kwargs['headers'], {'x-goog-api-key': 'test-key'})

    def test_gemini_key_validation_reports_unavailable_model(self):
        with patch('rpc.core_methods.httpx.get') as get:
            get.return_value.status_code = 404
            response = Resposta(*call('config.test_llm_key', {'key': 'test-key'}))
        self.assertFalse(response.data['ok'])
        self.assertIn('GEMINI_MODEL', response.data['reason'])


class SQLiteConcorrenciaESegurancaTests(unittest.TestCase):
    """Verifica comportamento concorrente e travas de segurança do SQLite."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.addCleanup(close_dados)
        self.path = Path(self.pasta.name) / "dados.db"
        self._gravar(self.path, 3)

    def _gravar(self, path, linhas):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE t (i INTEGER)")
        conn.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(linhas)])
        conn.commit()
        conn.close()

    def _contar(self):
        with connect_dados(path=self.path) as conn:
            return conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]

    def test_leitura_e_atualizacao_externa(self):
        self.assertEqual(self._contar(), 3)
        conn = sqlite3.connect(str(self.path))
        conn.execute("INSERT INTO t VALUES (99)")
        conn.commit()
        conn.close()
        self.assertEqual(self._contar(), 4)

    def test_consultas_concorrentes_em_threads(self):
        erros = []

        def consultar():
            try:
                for _ in range(20):
                    self._contar()
            except Exception as exc:
                erros.append(exc)

        threads = [threading.Thread(target=consultar) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(erros, [])

    def test_authorizer_bloqueia_escrita_e_comandos_perigosos(self):
        with connect_dados(path=self.path) as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("CREATE TABLE z (i INTEGER)")
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("INSERT INTO t VALUES (100)")
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("DROP TABLE t")
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("ATTACH DATABASE '/tmp/injetado.db' AS inj")


class CaminhosTests(unittest.TestCase):
    """Os caminhos acompanham o ambiente atual, como no app (sem valores fixados no import)."""

    def test_pasta_padrao_e_a_mesma_do_tauri(self):
        from core.datastore import data_dir

        with tempfile.TemporaryDirectory() as base, patch.dict(os.environ, {"XDG_DATA_HOME": base}):
            os.environ.pop("ORACULO_DATA_DIR", None)
            self.assertEqual(data_dir(), Path(base) / "br.edu.ifes.leds.oraculo-esx")

    def test_checkpointer_segue_o_caminho_atual_e_reabre_o_grafo(self):
        from agents.config import checkpoint_db_path
        from agents.orchestrator import graph

        async def caminho_do_grafo():
            async with graph.get_graph():
                return graph._path

        async def roteiro(a, b):
            with patch.dict(os.environ, {"ORACULO_CHECKPOINT_DB": a}):
                self.assertEqual(checkpoint_db_path(), a)
                primeiro = await caminho_do_grafo()
            with patch.dict(os.environ, {"ORACULO_CHECKPOINT_DB": b}):
                segundo = await caminho_do_grafo()
            await graph.close_graph()
            return primeiro, segundo

        with tempfile.TemporaryDirectory() as pasta:
            a, b = str(Path(pasta) / "a.db"), str(Path(pasta) / "b.db")
            self.assertEqual(asyncio.run(roteiro(a, b)), (a, b))


class PersistenciaTests(AppDbTestCase):
    """O que o ORM fazia sozinho e agora é feito à mão."""

    def test_banco_novo_e_banco_do_django_ficam_na_versao_atual(self):
        from core.schema import VERSAO

        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], VERSAO)
        tabelas = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertTrue({"core_contexto", "chat_message", "dashboard_widget", "analytics_text_embedding"} <= tabelas)

    def test_ids_com_hifens_no_codigo_e_hex_no_banco(self):
        tenant = Tenant(name="t").insert()
        self.assertEqual(len(tenant.id), 36)
        gravado = db.execute("SELECT id FROM core_tenant").fetchone()[0]
        self.assertEqual(gravado, tenant.id.replace("-", ""))
        self.assertEqual(Tenant.first("id = ?", [db.to_db_id(tenant.id)]).name, "t")

    def test_apagar_conversa_apaga_mensagens_e_solta_auditoria(self):
        from core.records import Conversation, Message, QueryExecution, delete_conversation

        user = get_local_user()
        ctx = Contexto(tenant_id=user.tenant_id, slug="c", name="C").insert()
        conv = Conversation(user_id=user.id, tenant_id=user.tenant_id, contexto_id=ctx.id).insert()
        msg = Message(conversation_id=conv.id, role="assistant", content="x", metadata={"sql": "SELECT 1"}).insert()
        qe = QueryExecution(tenant_id=user.tenant_id, message_id=msg.id, generated_sql="SELECT 1").insert()
        delete_conversation(conv.id)
        self.assertEqual(Message.count(), 0)
        self.assertEqual(Conversation.count(), 0)
        self.assertIsNone(QueryExecution.first("id = ?", [db.to_db_id(qe.id)]).message_id)

    def test_update_com_campos_nao_renova_updated_at(self):
        tenant = Tenant(name="t").insert()
        antes = tenant.updated_at
        tenant.name = "u"
        tenant.update("name")
        self.assertEqual(Tenant.first().updated_at, antes)
        tenant.update()
        self.assertGreater(Tenant.first().updated_at, antes)

    def test_usuario_local_e_unico(self):
        a, b = get_local_user(), get_local_user()
        self.assertEqual(a.id, b.id)
        self.assertTrue(a.is_staff)
        self.assertTrue(a.password.startswith("!"))


if __name__ == "__main__":
    unittest.main()
