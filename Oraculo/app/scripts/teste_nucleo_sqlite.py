"""Teste do núcleo SQLite do Oráculo desktop, sem LLM (embeddings e modelo falsos)."""
import asyncio
import os
import sqlite3
import sys
from pathlib import Path

API_DIR = Path(sys.argv[1])
DATA_DIR = Path(os.environ["ORACULO_DATA_DIR"])
sys.path.insert(0, str(API_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bi_agent_api.settings")
os.environ["ORACULO_EXPOSED_VIEWS"] = "vfactvendasresolved,v_resumo"
os.environ["ORACULO_SENSITIVE_COLUMNS"] = "vfactvendasresolved.cliente_cpf"

ok = 0
falhas = []


def check(nome, cond, detalhe=""):
    global ok
    if cond:
        ok += 1
        print(f"  OK   {nome}")
    else:
        falhas.append(nome)
        print(f"  FALHA {nome} {detalhe}")


# ── 1. dados.db fictício com views em níveis ───────────────────────────────
dados = DATA_DIR / "dados.db"
dados.unlink(missing_ok=True)
c = sqlite3.connect(dados)
c.executescript("""
CREATE TABLE vendas(id_venda INTEGER, produto TEXT, categoria_produto TEXT, segmento_produto TEXT,
  cliente TEXT, cliente_cpf TEXT, porte_cliente TEXT, setor_cliente TEXT, cidade TEXT, estado TEXT, regiao TEXT,
  canal TEXT, vendedor TEXT, equipe_vendas TEXT, regiao_vendedor TEXT, receita_liquida REAL, ano INT, mes INT, trimestre INT);
INSERT INTO vendas VALUES
 (1,'Notebook','Eletrônicos','B2B','ACME','111','Grande','Indústria','Vitória','ES','Sudeste','Site','Ana','Alpha','Sudeste',5000,2025,1,1),
 (2,'Mouse','Periféricos','B2C','Beta','222','Pequeno','Varejo','Serra','ES','Sudeste','Loja','Bia','Beta','Sudeste',100,2025,2,1),
 (3,'Notebook','Eletrônicos','B2B','Gama','333','Médio','Serviços','Rio','RJ','Sudeste','Site','Ana','Alpha','Sudeste',4500,2026,3,1);
CREATE VIEW v_base AS SELECT * FROM vendas;
CREATE VIEW vfactvendasresolved AS SELECT id_venda, produto, categoria_produto, segmento_produto, cliente, cliente_cpf,
  porte_cliente, setor_cliente, cidade, estado, regiao, canal, vendedor, equipe_vendas, regiao_vendedor,
  receita_liquida, ano, mes, trimestre FROM v_base;
CREATE VIEW v_resumo AS SELECT produto, SUM(receita_liquida) AS total FROM vfactvendasresolved GROUP BY produto;
""")
c.commit()
c.close()

import django  # noqa: E402

django.setup()

from langchain_core.embeddings.fake import DeterministicFakeEmbedding  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeListChatModel  # noqa: E402

from agents.bi_agent.agent import BIAgent  # noqa: E402
from agents.bi_agent.nodes.query_extractor import _search_knowledge  # noqa: E402
from agents.bi_agent.nodes.sql_validator import sql_validator  # noqa: E402
from agents.bi_agent.sql_security import validate_read_only_sql  # noqa: E402
from analytics_index.services import search_text_embeddings, sync_text_embeddings  # noqa: E402
from core.datastore import connect_dados, default_read_policy  # noqa: E402
from core.models import Tenant, User  # noqa: E402
from knowledge.models import KnowledgeItem  # noqa: E402

print("\n[1] Validação sintática (sqlglot, dialeto sqlite)")
v = lambda s: validate_read_only_sql(s)[0]  # noqa: E731
check("SELECT na view exposta", v("SELECT produto, SUM(receita_liquida) FROM vfactvendasresolved GROUP BY produto"))
check("CTE sobre view exposta", v("WITH x AS (SELECT * FROM v_resumo) SELECT * FROM x"))
check("view de views exposta", v("SELECT * FROM v_resumo"))
check("nega view intermediária", not v("SELECT * FROM v_base"))
check("nega tabela base", not v("SELECT * FROM vendas"))
check("nega escrita", not v("DELETE FROM vfactvendasresolved"))
check("nega duas instruções", not v("SELECT 1 FROM v_resumo; SELECT 2 FROM v_resumo"))

print("\n[2] Authorizer + EXPLAIN no dados.db (validator)")
st = lambda s: {"generated_sql": s, "db_schema_name": None}  # noqa: E731
check("validator aceita view exposta", sql_validator(st("SELECT produto FROM vfactvendasresolved"), None, "sqlite", True)["validation_result"]["valid"])
res = sql_validator(st("SELECT cliente_cpf FROM vfactvendasresolved"), None, "sqlite", True)["validation_result"]
check("validator nega coluna sensível", not res["valid"] and "prohibited" in res["error"], res)
with connect_dados(default_read_policy()) as conn:
    try:
        conn.execute("SELECT * FROM vendas").fetchall()
        check("authorizer nega tabela base mesmo sem sqlglot", False)
    except sqlite3.DatabaseError:
        check("authorizer nega tabela base mesmo sem sqlglot", True)
    try:
        conn.execute("CREATE TEMP TABLE t(x)")
        check("conexão é só leitura", False)
    except sqlite3.DatabaseError:
        check("conexão é só leitura", True)

print("\n[3] execute_query sem corte de linhas")
agent = BIAgent(llm_model=FakeListChatModel(responses=["x"]), embedder=DeterministicFakeEmbedding(size=1024))
rows = agent.execute_query("SELECT produto, receita_liquida FROM vfactvendasresolved")
check("devolve todas as linhas (3)", len(rows) == 3, rows)
check("max_rows explícito corta", len(agent.execute_query("SELECT produto FROM vfactvendasresolved", max_rows=1)) == 1)
check("erro vira dict de erro", "error" in agent.execute_query("SELECT cliente_cpf FROM vfactvendasresolved")[0])

print("\n[4] Vetores no app.db (BLOB float32 + numpy)")
emb = DeterministicFakeEmbedding(size=1024)
tenant, _ = Tenant.objects.get_or_create(name="padrao")
KnowledgeItem.objects.filter(tenant=tenant).delete()
textos = ["receita por produto", "clientes por estado", "vendas por canal"]
for t in textos:
    KnowledgeItem.objects.create(tenant=tenant, item_type="query_example", content=t, embedding=emb.embed_query(t))
item = KnowledgeItem.objects.filter(tenant=tenant).first()
check("embedding volta como vetor de 1024", item.embedding is not None and item.embedding.shape == (1024,))
achados = _search_knowledge(str(tenant.id), emb.embed_query("clientes por estado"), "query_example")
check("busca acha o item idêntico primeiro", achados and achados[0].content == "clientes por estado", [a.content for a in achados])

print("\n[5] Índice de valores lendo do dados.db")
from analytics_index.models import AnalyticsTextEmbedding  # noqa: E402

AnalyticsTextEmbedding.objects.filter(tenant=tenant).delete()
resumo = sync_text_embeddings(tenant, emb)
check("sincronizou valores distintos (3)", resumo["created"] == 3, resumo)
check("segunda execução não refaz embeddings", sync_text_embeddings(tenant, emb)["created"] == 0)
alvo = search_text_embeddings(tenant, emb.embed_query("x"), top_k=2)
check("busca de valores devolve top_k", len(alvo) == 2)

print("\n[6] Endpoints do dashboard (SQL cru portado)")
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

from dashboard import views as dv  # noqa: E402

user, _ = User.objects.get_or_create(username="local", defaults={"tenant": tenant})
fac = APIRequestFactory()
for nome, fn, params in [("kpis", dv.kpis, {}), ("charts", dv.charts, {}), ("projects", dv.projects, {"area": "eletr"}),
                         ("top_projects", dv.top_projects, {})]:
    req = fac.get("/x", params)
    force_authenticate(req, user=user)
    resp = fn(req)
    check(f"{nome} responde 200", resp.status_code == 200, getattr(resp, "data", None))
req = fac.get("/x")
force_authenticate(req, user=user)
charts = dv.charts(req).data
check("filtros JSON viram lista", isinstance(charts.get("anos_disponiveis"), list) and charts["anos_disponiveis"] == [2025, 2026], charts.get("anos_disponiveis"))
req = fac.get("/x", {"area": "eletr"})
force_authenticate(req, user=user)
proj = dv.projects(req).data
check("projects mantém status como texto e filtros como lista",
      proj["data"][0]["status"] in {"Grande", "Médio"} and isinstance(proj["filtros_disponiveis"]["status"], list), proj)
req = fac.get("/x")
force_authenticate(req, user=user)
resp = dv.system_status(req)
check("system_status responde 200", resp.status_code == 200, resp.data)


print("\n[7] Checkpointer SQLite no app.db")
from agents.orchestrator.graph import get_graph  # noqa: E402


async def testa_checkpointer():
    async with get_graph() as graph:
        return graph is not None


check("get_graph compila com AsyncSqliteSaver", asyncio.run(testa_checkpointer()))
with sqlite3.connect(DATA_DIR / "app.db") as conn:
    tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
check("tabelas checkpoints/writes ao lado do Django", {"checkpoints", "writes", "core_user"} <= tabelas)

print(f"\nResultado: {ok} OK, {len(falhas)} falha(s)")
if falhas:
    print("Falhas:", falhas)
    sys.exit(1)
