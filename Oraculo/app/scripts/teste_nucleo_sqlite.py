"""Teste do núcleo SQLite e dos contextos do Oráculo desktop, sem LLM (embeddings e modelo falsos).

Uso (de backend/api, com app.db já migrado):
    ORACULO_DATA_DIR=/tmp/oraculo-teste JWT_SECRET=x MISTRAL_API_KEY=x \
        ../../.venv/bin/python ../../scripts/teste_nucleo_sqlite.py "$PWD"
"""
import asyncio
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

API_DIR = Path(sys.argv[1])
REPO_DIR = API_DIR.parent.parent
DATA_DIR = Path(os.environ["ORACULO_DATA_DIR"])
EXEMPLO = REPO_DIR / "contexts" / "exemplo-vendas"
sys.path.insert(0, str(API_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bi_agent_api.settings")

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


# ── dados.db fictício com views em níveis ───────────────────────────────────
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
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

from agents.bi_agent.agent import BIAgent  # noqa: E402
from agents.bi_agent.nodes.query_extractor import _search_knowledge  # noqa: E402
from agents.bi_agent.nodes.sql_validator import sql_validator  # noqa: E402
from agents.bi_agent.sql_security import validate_read_only_sql  # noqa: E402
from analytics_index.services import search_text_embeddings  # noqa: E402
from core.contexts import (  # noqa: E402
    build_system_prompt,
    index_contexto,
    load_context_dir,
    pick_contexto,
    read_policy_for,
)
from core.datastore import connect_dados  # noqa: E402
from core.models import Contexto, Tenant, User  # noqa: E402
from knowledge.models import KnowledgeItem  # noqa: E402

emb = DeterministicFakeEmbedding(size=1024)
tenant, _ = Tenant.objects.get_or_create(name="padrao")
user, _ = User.objects.get_or_create(username="local", defaults={"tenant": tenant})
fac = APIRequestFactory()

print("\n[1] Validação sintática (sqlglot, dialeto sqlite)")
views = {"vfactvendasresolved", "v_resumo"}
v = lambda s: validate_read_only_sql(s, views)[0]  # noqa: E731
check("SELECT na view exposta", v("SELECT produto, SUM(receita_liquida) FROM vfactvendasresolved GROUP BY produto"))
check("CTE sobre view exposta", v("WITH x AS (SELECT * FROM v_resumo) SELECT * FROM x"))
check("view de views exposta", v("SELECT * FROM v_resumo"))
check("nega view intermediária", not v("SELECT * FROM v_base"))
check("nega tabela base", not v("SELECT * FROM vendas"))
check("nega escrita", not v("DELETE FROM vfactvendasresolved"))
check("nega duas instruções", not v("SELECT 1 FROM v_resumo; SELECT 2 FROM v_resumo"))
check("sem views permitidas nega tudo", not validate_read_only_sql("SELECT * FROM v_resumo", set())[0])

print("\n[2] Carga do contexto de exemplo (views.json, rules.md, examples.json)")
contexto, exemplos, erros = load_context_dir(EXEMPLO, tenant)
check("contexto de exemplo válido e ativo", not erros and contexto.is_active, erros)
check("4 exemplos lidos", len(exemplos) == 4, len(exemplos))
ruim = DATA_DIR / "ctx-ruim"
shutil.rmtree(ruim, ignore_errors=True)
ruim.mkdir()
(ruim / "views.json").write_text(json.dumps({
    "contexto": "ruim",
    "views": [
        {"name": "nao_existe"},
        {"name": "vfactvendasresolved", "sensitive_columns": ["cpf_errado"], "embed_columns": ["cliente_cpf"]},
    ],
}), encoding="utf-8")
ctx_ruim, _, erros_ruim = load_context_dir(ruim, tenant)
check("view inexistente vira erro", any("nao_existe" in e for e in erros_ruim), erros_ruim)
check("coluna declarada inexistente vira erro", any("cpf_errado" in e for e in erros_ruim), erros_ruim)
check("contexto inválido fica inativo", not ctx_ruim.is_active)

print("\n[3] Política do contexto no dados.db (authorizer + EXPLAIN)")
cid = str(contexto.id)
st = lambda s, c=cid: {"generated_sql": s, "contexto_id": c}  # noqa: E731
check("validator aceita view exposta", sql_validator(st("SELECT produto FROM vfactvendasresolved"), None, "sqlite", True)["validation_result"]["valid"])
res = sql_validator(st("SELECT cliente_cpf FROM vfactvendasresolved"), None, "sqlite", True)["validation_result"]
check("validator nega coluna sensível", not res["valid"] and "prohibited" in res["error"], res)
check("validator sem contexto nega", not sql_validator(st("SELECT produto FROM v_resumo", None), None, "sqlite", True)["validation_result"]["valid"])
with connect_dados(read_policy_for(contexto)) as conn:
    try:
        conn.execute("SELECT * FROM vendas").fetchall()
        check("authorizer nega tabela base", False)
    except sqlite3.DatabaseError:
        check("authorizer nega tabela base", True)
    try:
        conn.execute("CREATE TEMP TABLE t(x)")
        check("conexão é só leitura", False)
    except sqlite3.DatabaseError:
        check("conexão é só leitura", True)

print("\n[4] execute_query com o contexto, sem corte")
agent = BIAgent(llm_model=FakeListChatModel(responses=["x"]), embedder=emb)
check("devolve todas as linhas (3)", len(agent.execute_query("SELECT produto FROM vfactvendasresolved", cid)) == 3)
check("max_rows explícito corta", len(agent.execute_query("SELECT produto FROM vfactvendasresolved", cid, max_rows=1)) == 1)
check("sem contexto vira erro", "error" in agent.execute_query("SELECT produto FROM v_resumo", None)[0])
sem_ctx = agent.ask("qual a receita?", str(tenant.id), None, "t1")
check("ask sem contexto não gera SQL", sem_ctx["sql"] is None and not sem_ctx["valid"], sem_ctx)

print("\n[5] Prompt montado a partir do contexto")
prompt = build_system_prompt(contexto)
check("prompt lista as views expostas", "vfactvendasresolved(" in prompt and "v_resumo(" in prompt)
check("prompt não mostra coluna sensível", "cliente_cpf" not in prompt)
check("prompt traz as regras do rules.md", "SUM(receita_liquida)" in prompt)
check("prompt não menciona view intermediária", "v_base" not in prompt)

print("\n[6] Indexação do contexto (RAG + valores) e busca")
resumo = index_contexto(contexto, emb, exemplos)
check("6 itens de RAG (ddl + regras + 4 exemplos)", resumo["knowledge_items"] == 6, resumo)
check("2 combinações de valores embedadas", resumo["values"]["created"] == 2, resumo["values"])
ddl = KnowledgeItem.objects.get(contexto=contexto, item_type="ddl")
check("DDL do RAG sem coluna sensível", "cliente_cpf" not in ddl.content)
KnowledgeItem.objects.create(tenant=tenant, contexto=None, item_type="doc", content="regra genérica", embedding=emb.embed_query("regra genérica"))
outro = Contexto.objects.create(tenant=tenant, slug="outro", name="Outro", views=[{"name": "v_resumo"}])
KnowledgeItem.objects.create(tenant=tenant, contexto=outro, item_type="doc", content="regra do outro", embedding=emb.embed_query("regra do outro"))
docs = [i.content for i in _search_knowledge(str(tenant.id), cid, emb.embed_query("x"), "doc")]
check("RAG traz itens do contexto e genéricos", "regra genérica" in docs and contexto.rules in docs, docs)
check("RAG não traz itens de outro contexto", "regra do outro" not in docs, docs)
check("busca de valores do contexto", len(search_text_embeddings(contexto, emb.embed_query("x"), top_k=5)) == 2)

print("\n[7] Escolha de contexto para conversa nova")
check("com dois ativos e nenhum pedido: exige escolha", pick_contexto(tenant) is None)
check("pedido explícito resolve", pick_contexto(tenant, cid) == contexto)
outro.is_active = False
outro.save()
check("com um ativo: usa ele", pick_contexto(tenant) == contexto)

from chat.views import _conversation_for  # noqa: E402
from rest_framework.exceptions import ValidationError  # noqa: E402

conv = _conversation_for(user, tenant, None, None, "teste")
check("conversa nova recebe o contexto", conv.contexto_id == contexto.id)
outro.is_active = True
outro.save()
try:
    _conversation_for(user, tenant, None, None, "teste")
    check("conversa nova sem contexto com dois ativos dá 400", False)
except ValidationError:
    check("conversa nova sem contexto com dois ativos dá 400", True)
check("conversa existente mantém o contexto", _conversation_for(user, tenant, conv.id, str(outro.id), "x").contexto_id == contexto.id)
outro.delete()

print("\n[8] Endpoints")
from core.views import contextos as contextos_view  # noqa: E402
from dashboard import views as dv  # noqa: E402
from dashboard.models import Dashboard, Widget  # noqa: E402

req = fac.get("/x")
force_authenticate(req, user=user)
lista = contextos_view(req).data
check("api/contextos lista o ativo", [c["slug"] for c in lista] == ["exemplo-vendas"], lista)
check("api/contextos não expõe colunas sensíveis", "cliente_cpf" not in json.dumps(lista))
painel = Dashboard.objects.create(user=user, tenant=tenant, name="principal")
widget = Widget.objects.create(dashboard=painel, contexto=contexto, title="w", question_original="q",
                               sql_validated="SELECT produto, total FROM v_resumo", chart_type="bar")
req = fac.post("/x")
force_authenticate(req, user=user)
resp = dv.WidgetViewSet.as_view({"post": "refresh"})(req, pk=str(widget.id))
check("widget roda com a política do seu contexto", resp.status_code == 200 and resp.data["widget_status"] == "OK" and len(resp.data["data"]) == 2, resp.data)
for nome, fn in [("kpis", dv.kpis), ("charts", dv.charts), ("projects", dv.projects), ("top_projects", dv.top_projects)]:
    req = fac.get("/x")
    force_authenticate(req, user=user)
    check(f"{nome} (painel de vendas de demonstração) responde 200", fn(req).status_code == 200)
pasta = DATA_DIR / "contexts"
shutil.rmtree(pasta, ignore_errors=True)
shutil.copytree(EXEMPLO, pasta / "exemplo-vendas")
user.is_staff = True
user.save()
req = fac.post("/x")
force_authenticate(req, user=user)
resp = dv.data_bootstrap(req)
check("recarga de contextos da pasta de dados", resp.status_code == 200 and resp.data["contextos"][0]["ativo"], resp.data)

print("\n[9] Checkpointer SQLite no app.db")
from agents.orchestrator.graph import get_graph  # noqa: E402


async def testa_checkpointer():
    async with get_graph() as graph:
        return graph is not None


check("get_graph compila com AsyncSqliteSaver", asyncio.run(testa_checkpointer()))
with sqlite3.connect(DATA_DIR / "app.db") as conn:
    tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
check("tabelas checkpoints/writes ao lado do Django", {"checkpoints", "writes", "core_contexto"} <= tabelas)

print(f"\nResultado: {ok} OK, {len(falhas)} falha(s)")
if falhas:
    print("Falhas:", falhas)
    sys.exit(1)
