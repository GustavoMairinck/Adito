from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import duckdb
from django.test import TestCase

from agents.bi_agent.agent import BIAgent
from agents.bi_agent.sql_security import validate_read_only_sql
from analytics_index.services import fetch_distinct_candidates
from core.contexts import describe_views, load_context_dir, view_columns
from core.datastore import ReadPolicy, connect_dados
from core.models import Tenant

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

