"""
Testes unitários e de integração do Datastore SQLite (dados.db) e Authorizer de Segurança.
Execução: PYTHONPATH=Adito/app/backend/nucleo Adito/app/.venv/bin/python -m unittest core.test_datastore_sqlite
"""
from __future__ import annotations

import os
import sqlite3
import sys
import unittest
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[5]
NUCLEO_DIR = RAIZ_REPO / "Adito" / "app" / "backend" / "nucleo"
DADOS_DB_PATH = RAIZ_REPO / "Adito" / "app" / "data" / "dados.db"

if str(NUCLEO_DIR) not in sys.path:
    sys.path.insert(0, str(NUCLEO_DIR))

from core.datastore import (
    ReadPolicy,
    close_dados,
    connect_dados,
    custom_like,
    strip_accents,
    transpile_sql,
)


class DatastoreSQLiteSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DADOS_DB_PATH.exists():
            raise unittest.SkipTest(f"dados.db não encontrado em {DADOS_DB_PATH}")

    def setUp(self):
        close_dados()

    def tearDown(self):
        close_dados()

    def test_strip_accents(self):
        self.assertEqual(strip_accents("Vitória"), "vitoria")
        self.assertEqual(strip_accents("AÇÃO de EXTENSÃO"), "acao de extensao")
        self.assertEqual(strip_accents("José Da Silva"), "jose da silva")
        self.assertEqual(strip_accents(None), "")

    def test_custom_like_direto(self):
        self.assertEqual(custom_like("%vitoria%", "Campus Vitória"), 1)
        self.assertEqual(custom_like("%serra%", "Campus SERRA"), 1)
        self.assertEqual(custom_like("%acoes%", "Ações Comunitárias"), 1)
        self.assertEqual(custom_like("%nao_existe%", "Campus Vitória"), 0)

    def test_custom_like_com_escape(self):
        # `x LIKE y ESCAPE z` chama like/3: segue sem acento e sem caixa, e o escape vale.
        self.assertEqual(custom_like("%robotica%", "Robótica educacional 100%", "!"), 1)
        self.assertEqual(custom_like("%ACAO%", "AÇÃO", "!"), 1)
        self.assertEqual(custom_like("%100!%%", "Robótica educacional 100%", "!"), 1)
        self.assertEqual(custom_like("%100!%%", "Robótica educacional 1000", "!"), 0)
        self.assertEqual(custom_like("%a!_b%", "a_b", "!"), 1)
        self.assertEqual(custom_like("%a!_b%", "axb", "!"), 0)
        self.assertEqual(custom_like("%!!%", "sim!", "!"), 1)
        with self.assertRaises(ValueError):
            custom_like("%a%", "a", "!!")

    def test_authorizer_bloqueia_mutacoes_e_ddl(self):
        conn = connect_dados(path=DADOS_DB_PATH)
        try:
            # SELECT em view é permitido
            cur = conn.execute("SELECT COUNT(*) FROM vfact_extensao_acao_resolved")
            count = cur.fetchone()[0]
            self.assertGreater(count, 0)

            # PRAGMA de leitura seguro é permitido
            cur_info = conn._conn.execute("PRAGMA table_info(vfact_extensao_acao_resolved)")
            self.assertGreater(len(cur_info.fetchall()), 0)

            # PRAGMA perigoso de escrita é bloqueado pelo authorizer
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("PRAGMA writable_schema = ON")

            # INSERT é bloqueado pelo authorizer
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("INSERT INTO pessoa (id, nome) VALUES (999999, 'Hacker')")

            # UPDATE é bloqueado pelo authorizer
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("UPDATE pessoa SET nome = 'Hacker' WHERE id = 1")

            # DELETE é bloqueado pelo authorizer
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("DELETE FROM pessoa WHERE id = 1")

            # DROP VIEW é bloqueado pelo authorizer
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("DROP VIEW vfact_extensao_acao_resolved")

            # ATTACH é bloqueado pelo authorizer
            with self.assertRaises(sqlite3.DatabaseError):
                conn._conn.execute("ATTACH DATABASE '/tmp/injetado.db' AS injetado")
        finally:
            conn.close()

    def test_custom_like_em_query_sqlite(self):
        conn = connect_dados(path=DADOS_DB_PATH)
        try:
            # Busca textual insensível a acento e maiúsculas/minúsculas:
            # "analise" sem acento deve casar com "Análise"
            cur1 = conn.execute(
                "SELECT COUNT(*) FROM vfact_producao_cientifica_resolved WHERE titulo_producao LIKE '%analise%'"
            )
            total_sem_acento = cur1.fetchone()[0]

            cur2 = conn.execute(
                "SELECT COUNT(*) FROM vfact_producao_cientifica_resolved WHERE titulo_producao LIKE '%Análise%'"
            )
            total_com_acento = cur2.fetchone()[0]

            self.assertGreater(total_sem_acento, 0)
            self.assertEqual(total_sem_acento, total_com_acento)

            # Busca por "serra" minúsculo casando com "Serra"
            cur3 = conn.execute(
                "SELECT COUNT(*) FROM vfact_extensao_acao_resolved WHERE campus LIKE '%serra%'"
            )
            total_serra = cur3.fetchone()[0]
            self.assertGreater(total_serra, 0)
        finally:
            conn.close()

    def test_transpile_sqlglot_ilike_para_sqlite(self):
        conn = connect_dados(path=DADOS_DB_PATH)
        try:
            # Query com ILIKE deve ser convertida para SQLite nativo e rodar com sucesso
            cur = conn.execute(
                "SELECT tipo_acao, COUNT(*) FROM vfact_extensao_acao_resolved WHERE campus ILIKE '%Serra%' GROUP BY tipo_acao"
            )
            rows = cur.fetchall()
            self.assertGreater(len(rows), 0)
        finally:
            conn.close()

    def test_read_policy_bloqueia_tabelas_internas_e_colunas_sensiveis(self):
        policy = ReadPolicy(
            exposed_views=frozenset({"vfact_extensao_acao_resolved"}),
            sensitive_columns=frozenset({("vfact_extensao_acao_resolved", "coordenador_cpf")}),
        )
        conn = connect_dados(policy=policy, path=DADOS_DB_PATH)
        try:
            # Acesso a view exposta é permitido
            cur = conn.execute("SELECT id_acao, campus FROM vfact_extensao_acao_resolved LIMIT 5")
            rows = cur.fetchall()
            self.assertEqual(len(rows), 5)

            # SELECT * é bloqueado
            with self.assertRaises(PermissionError):
                conn.execute("SELECT * FROM vfact_extensao_acao_resolved")

            # Coluna sensível explicitada é bloqueada
            with self.assertRaises(PermissionError):
                conn.execute("SELECT coordenador_cpf FROM vfact_extensao_acao_resolved")

            # Tabela base interna 3FN não exposta é bloqueada pelo ReadPolicy
            with self.assertRaises(PermissionError):
                conn.execute("SELECT id, nome FROM pessoa")
        finally:
            conn.close()

    def test_todas_as_6_views_dinamicas_operam_com_sucesso(self):
        views_esperadas = [
            "vfact_extensao_acao_resolved",
            "vfact_extensao_participacao_resolved",
            "vfact_projeto_pesquisa_resolved",
            "vfact_orientacao_bolsa_resolved",
            "vfact_producao_cientifica_resolved",
            "vfact_grupo_pesquisa_membro_resolved",
        ]
        conn = connect_dados(path=DADOS_DB_PATH)
        try:
            for v in views_esperadas:
                cur = conn.execute(f"SELECT COUNT(*) AS total FROM {v}")
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertGreater(row[0], 0, f"View {v} está vazia!")
        finally:
            conn.close()

    def test_campos_novos_v2_fatos(self):
        conn = connect_dados(path=DADOS_DB_PATH)
        try:
            # 1. Producao cientifica: qtd_autorias, flag_obra_unica, flag_software_sem_patente, instituicao_vinculo
            cur = conn.execute(
                "SELECT qtd_autorias, flag_obra_unica, flag_software_sem_patente, instituicao_vinculo "
                "FROM vfact_producao_cientifica_resolved LIMIT 1"
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertIn("qtd_autorias", row.keys())
            self.assertIn("flag_obra_unica", row.keys())
            self.assertIn("flag_software_sem_patente", row.keys())
            self.assertIn("instituicao_vinculo", row.keys())

            # 2. Orientacao bolsa: duracao_meses_efetiva, investimento_total_estimado, investimento_previsto_original, titulacao_orientador
            cur = conn.execute(
                "SELECT duracao_meses_efetiva, investimento_total_estimado, investimento_previsto_original, titulacao_orientador "
                "FROM vfact_orientacao_bolsa_resolved LIMIT 1"
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertIn("duracao_meses_efetiva", row.keys())
            self.assertIn("investimento_total_estimado", row.keys())
            self.assertIn("investimento_previsto_original", row.keys())
            self.assertIn("titulacao_orientador", row.keys())

            # 3. Extensao acao: qtd_atividades_vinculadas, flag_relatorio_aprovado
            cur = conn.execute(
                "SELECT qtd_atividades_vinculadas, flag_relatorio_aprovado FROM vfact_extensao_acao_resolved LIMIT 1"
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertIn("qtd_atividades_vinculadas", row.keys())
            self.assertIn("flag_relatorio_aprovado", row.keys())

            # 4. Projeto pesquisa: duracao_meses_prevista, flag_projeto_completo, parceiros_demandantes
            cur = conn.execute(
                "SELECT duracao_meses_prevista, flag_projeto_completo, parceiros_demandantes FROM vfact_projeto_pesquisa_resolved LIMIT 1"
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertIn("duracao_meses_prevista", row.keys())
            self.assertIn("flag_projeto_completo", row.keys())
            self.assertIn("parceiros_demandantes", row.keys())
        finally:
            conn.close()


class DashboardRpcSQLiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DADOS_DB_PATH.exists():
            raise unittest.SkipTest(f"dados.db não encontrado em {DADOS_DB_PATH}")

    def setUp(self):
        close_dados()

    def tearDown(self):
        close_dados()

    def test_dashboard_kpis(self):
        from rpc.dashboard import kpis
        res = kpis({})
        self.assertIn("total_investido", res)
        self.assertIn("projetos_ativos", res)
        self.assertIn("equipe_alocada", res)
        self.assertGreater(res["total_investido"], 0)
        self.assertGreater(res["projetos_ativos"], 0)
        self.assertGreater(res["equipe_alocada"], 0)

    def test_dashboard_top_projects(self):
        from rpc.dashboard import top_projects
        rows = top_projects({})
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)
        self.assertIn("nome", rows[0])
        self.assertIn("valor", rows[0])
        self.assertIn("valor_formatado", rows[0])

    def test_dashboard_charts(self):
        from rpc.dashboard import charts
        res = charts({})
        self.assertIn("por_ano", res)
        self.assertIn("mensal", res)
        self.assertIn("anos_disponiveis", res)
        self.assertIn("areas_disponiveis", res)
        self.assertIn("modalidades_disponiveis", res)
        self.assertIn("statuses_disponiveis", res)
        self.assertIn("ano_vigente", res)
        self.assertGreater(len(res["por_ano"]), 0)
        self.assertGreater(len(res["areas_disponiveis"]), 0)


if __name__ == "__main__":
    unittest.main()
