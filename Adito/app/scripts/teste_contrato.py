"""Teste de contrato do núcleo do Adito: cada chamada que o front faz, com status e JSON.

Roda o roteiro contra o núcleo local e compara com a referência (`contrato/referencia.json`),
gravada com o servidor Django antes de ele ser removido: é a garantia de que as telas recebem
o mesmo que antes. Os dados são sintéticos (nenhum dado pessoal) e o LLM é substituído por um
grafo falso, então o teste não usa rede nem chave.

Uso (de Adito/app):
    .venv/bin/python scripts/teste_contrato.py            # compara com a referência
    .venv/bin/python scripts/teste_contrato.py --gravar   # regrava (só se a mudança de contrato for intencional)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
API_DIR = APP_DIR / "backend" / "nucleo"
REFERENCIA = Path(__file__).resolve().parent / "contrato" / "referencia.json"

DATA_DIR = Path(tempfile.mkdtemp(prefix="adito-contrato-"))
os.environ["ADITO_DATA_DIR"] = str(DATA_DIR)
os.environ["ADITO_LOCAL_TOKEN"] = "token-contrato"
os.environ["GEMINI_API_KEY"] = "chave-falsa"
os.environ.pop("GOOGLE_API_KEY", None)
os.environ.pop("ADITO_DADOS_DB", None)
os.environ.pop("ADITO_APP_DB", None)
os.environ.pop("ADITO_CHECKPOINT_DB", None)
os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
sys.path.insert(0, str(API_DIR))

VIEW = "vfact_orientacao_bolsa_resolved"


# ── Dados sintéticos ─────────────────────────────────────────────────────────

def criar_dados() -> None:
    import sqlite3

    conn = sqlite3.connect(str(DATA_DIR / "dados.db"))
    conn.execute(f"""
        CREATE TABLE {VIEW} (
            id_orientacao INTEGER, ano INTEGER, grande_area TEXT, programa_fomento TEXT,
            modalidade TEXT, titulo_projeto TEXT, titulo_edital TEXT,
            investimento_total_estimado REAL, nome_orientador TEXT,
            agencia_financiadora TEXT, data_inicio TEXT, cpf_orientador TEXT
        )
    """)
    areas = ["Exatas", "Humanas", "Saúde"]
    programas = ["PIBIC", "PIBITI", "Voluntário"]
    rows = []
    for i in range(1, 41):
        rows.append((
            i, 2024 + i % 3, areas[i % 3], programas[i % 3], f"Modalidade {i % 2}",
            f"Projeto {i % 12:02d}", f"Edital {i % 4}", float(Decimal(f"{(i * 137) % 900 + 100}.50")),
            f"Pessoa {chr(65 + i % 7)}", f"Agência {i % 2}", str(date(2024, 1 + i % 12, 1)), f"000.000.000-{i:02d}",
        ))
    conn.executemany(f"INSERT INTO {VIEW} VALUES ({', '.join('?' * 12)})", rows)
    conn.execute("CREATE VIEW dim_area AS SELECT DISTINCT grande_area AS nome FROM " + VIEW)
    conn.commit()
    conn.close()

    ctx = DATA_DIR / "contexts" / "ctx-contrato"
    ctx.mkdir(parents=True)
    (ctx / "views.json").write_text(json.dumps({
        "contexto": "ctx-contrato",
        "nome": "Contrato",
        "descricao": "Contexto sintético do teste de contrato.",
        "ativo": True,
        "views": [
            {"name": VIEW, "description": "Uma linha por orientação.", "sensitive_columns": ["cpf_orientador"],
             "embed_columns": ["grande_area"]},
            {"name": "dim_area", "description": "Áreas.", "label": "Áreas"},
        ],
        "llm_row_limit": 20,
    }), encoding="utf-8")
    (ctx / "rules.md").write_text("Investimento: SUM(investimento_total_estimado)\n", encoding="utf-8")
    (ctx / "examples.json").write_text(json.dumps([
        {"question": "Investimento por ano?", "sql": f"SELECT ano, SUM(investimento_total_estimado) FROM {VIEW} GROUP BY ano"},
    ]), encoding="utf-8")


# ── Grafo falso (substitui o orquestrador com LLM) ──────────────────────────

class _Chunk:
    def __init__(self, text):
        self.text = text


def grafo_falso(sql: str, rows: list[dict]):
    class Grafo:
        async def astream(self, initial_state, config=None, stream_mode=None):
            yield "updates", {"orchestrator": {"calls": [{"intent": "bi_agent"}]}}
            yield "messages", (_Chunk("Olá"), {"langgraph_node": "conversational_agent"})
            yield "updates", {"mcp_tool_node": {
                "sql_used": sql, "graph": rows, "type": "analysis", "score": 1,
                "text_response": "Total calculado.", "final_response": "Total calculado.",
                "analysis_explanation": "Soma por ano.", "message": "", "suggestions": ["Por área?"],
                "related_attributes": [], "field_formats": {"total": "currency"},
            }}

    @asynccontextmanager
    async def get_graph():
        yield Grafo()

    return get_graph


SQL_OK = f"SELECT ano, SUM(investimento_total_estimado) AS total FROM {VIEW} GROUP BY ano ORDER BY ano"
ROWS_OK = [{"ano": 2024, "total": Decimal("10.50"), "inicio": date(2024, 1, 1)}]
SQL_QUEBRADO = "SELECT coluna_inexistente FROM " + VIEW


# ── Roteiro ──────────────────────────────────────────────────────────────────

async def roteiro(api) -> list[dict]:
    """Sequência de chamadas, na ordem em que as telas as usam. `api` é o adaptador da implementação."""
    out = []

    async def call(nome, method, params=None):
        status, body = await api.call(method, params or {})
        out.append({"nome": nome, "status": status, "body": body})
        return body

    async def stream(nome, method, params, sql=SQL_OK, rows=ROWS_OK):
        status, events = await api.stream(method, params, grafo_falso(sql, rows))
        out.append({"nome": nome, "status": status, "events": events})
        return events

    await call("health", "health")
    await call("me", "me")
    ctxs = await call("contextos", "contextos.list")
    cid = ctxs[0]["id"] if isinstance(ctxs, list) and ctxs else None

    await call("kpis", "dashboard.kpis")
    await call("kpis filtrado", "dashboard.kpis", {"ano": "2025", "area": "hum"})
    await call("top_projects", "dashboard.top_projects")
    await call("charts", "dashboard.charts", {"modalidade": "pib"})

    widget = await call("widgets.create", "widgets.create", {
        "title": "Total por ano", "question_original": "Total por ano?", "sql_validated": SQL_OK,
        "contexto": cid, "chart_type": "bar", "grid_w": 6, "grid_h": 4, "grid_x": 0, "grid_y": 0, "size": "medium",
    })
    await call("widgets.create inválido", "widgets.create", {"title": "x", "chart_type": "radar"})
    wid = widget.get("id") if isinstance(widget, dict) else None
    await call("widgets.list", "widgets.list", {"dashboard_id": "principal"})
    await call("widgets.update", "widgets.update", {"id": wid, "grid_x": 2, "grid_y": 1, "grid_w": 4, "size": "small"})
    await call("widgets.refresh", "widgets.refresh", {"id": wid})
    quebrado = await call("widgets.create quebrado", "widgets.create", {
        "title": "Quebrado", "question_original": "?", "sql_validated": SQL_QUEBRADO, "contexto": cid, "chart_type": "table",
    })
    await call("widgets.refresh quebrado", "widgets.refresh", {"id": quebrado.get("id") if isinstance(quebrado, dict) else None})
    await call("widgets.delete", "widgets.delete", {"id": wid})
    await call("widgets.refresh inexistente", "widgets.refresh", {"id": wid})
    await call("widgets.list depois", "widgets.list", {"dashboard_id": "principal"})

    events = await stream("chat.stream nova", "chat.stream", {"question": "Total por ano?", "contexto_id": cid})
    conv_id = next((e["data"].get("conversation_id") for e in events if e["event"] == "status"), None)
    await stream("chat.stream continua", "chat.stream",
                 {"question": "E por área?", "conversation_id": conv_id}, sql=SQL_QUEBRADO, rows=[])
    await stream("chat.stream local", "chat.stream", {"question": "Oi", "conversation_id": "local-123", "contexto_id": cid})
    await stream("chat.stream sem pergunta", "chat.stream", {"contexto_id": cid})
    await stream("chat.stream contexto inválido", "chat.stream",
                 {"question": "x", "contexto_id": "00000000-0000-0000-0000-000000000000"})
    del os.environ["GEMINI_API_KEY"]
    await stream("chat.stream sem chave", "chat.stream", {"question": "x", "contexto_id": cid})
    await call("me sem chave", "me")
    os.environ["GEMINI_API_KEY"] = "chave-falsa"

    convs = await call("conversations.list", "chat.conversations.list")
    msgs = [m for c in convs for m in c["messages"]] if isinstance(convs, list) else []
    assistentes = [m for m in msgs if m["role"] == "assistant"]
    for i, m in enumerate(assistentes):
        await call(f"message_rows {i}", "chat.message_rows", {"id": m["id"]})
    if msgs:
        await call("message_rows de pergunta", "chat.message_rows", {"id": msgs[0]["id"]})
    await call("query_executions", "admin.query_executions", {"limit": "100"})
    await call("query_executions inválidas", "admin.query_executions", {"limit": "100", "is_valid": "false"})
    await call("conversations.delete", "chat.conversations.delete", {"id": conv_id})
    await call("conversations.list depois", "chat.conversations.list")
    await call("query_executions depois", "admin.query_executions", {"limit": "100"})

    await call("test_llm_key vazia", "config.test_llm_key", {"key": "  "})
    await call("system_status", "admin.system_status")
    await call("trainings.create", "admin.trainings.create",
               {"type": "sql", "question": "Quantas orientações?", "content": f"SELECT COUNT(*) FROM {VIEW}"})
    await call("trainings.create sem pergunta", "admin.trainings.create", {"type": "sql", "content": "SELECT 1"})
    await call("system_status depois", "admin.system_status")
    await call("trainings.list", "admin.trainings.list")
    manual = await call("trainings.create com contexto", "admin.trainings.create",
                        {"type": "documentation", "content": "Bolsista é aluno com bolsa.", "contexto": cid})
    await call("trainings.create contexto inexistente", "admin.trainings.create",
               {"type": "documentation", "content": "x", "contexto": "00000000-0000-0000-0000-000000000000"})
    await call("trainings.retrain", "admin.trainings.retrain", {"contexto": cid})
    await call("trainings.list depois do retrain", "admin.trainings.list")
    mid = manual.get("id") if isinstance(manual, dict) else None
    await call("trainings.delete", "admin.trainings.delete", {"id": mid})
    await call("trainings.delete inexistente", "admin.trainings.delete", {"id": mid})
    await call("system_status depois do retrain", "admin.system_status")
    del os.environ["GEMINI_API_KEY"]
    await call("trainings.retrain sem chave", "admin.trainings.retrain", {"contexto": cid})
    os.environ["GEMINI_API_KEY"] = "chave-falsa"
    del os.environ["GEMINI_API_KEY"]
    await call("bootstrap sem chave", "admin.bootstrap")
    os.environ["GEMINI_API_KEY"] = "chave-falsa"
    await call("contextos depois", "contextos.list")
    return out


# ── Normalização (ids, datas e caminhos variam entre execuções) ─────────────

UUID_RE = re.compile(r"\b[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\b")
TS_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?\b")
VOLATEIS = {"latency_ms", "uptime", "url"}


def normalizar(obj, ids: dict):
    if isinstance(obj, dict):
        # list(DISTINCT ...) do DuckDB não tem ordem garantida.
        return {
            k: "<volátil>" if k in VOLATEIS
            else sorted(v, key=str) if k.endswith("disponiveis") and isinstance(v, list)
            else normalizar(v, ids)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [normalizar(v, ids) for v in obj]
    if isinstance(obj, str):
        if obj == "00000000-0000-0000-0000-000000000000":
            return obj

        def troca(m):
            chave = m.group(0).replace("-", "")
            return ids.setdefault(chave, f"<id{len(ids) + 1}>")

        s = UUID_RE.sub(troca, obj)
        s = TS_RE.sub("<data>", s)
        return s.replace(str(DATA_DIR), "<dados>")
    return obj


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gravar", action="store_true")
    parser.add_argument("--impl", default="rpc")
    args = parser.parse_args()

    criar_dados()
    from contrato_adaptadores import adaptador

    api = adaptador(args.impl)
    try:
        resultado = normalizar(asyncio.run(roteiro(api)), {})
        for item in resultado:
            # 200, 201 e 204 são o mesmo "deu certo" para o front.
            if 200 <= item["status"] < 300:
                item["status"] = "2xx"
    finally:
        shutil.rmtree(DATA_DIR, ignore_errors=True)

    if args.gravar:
        REFERENCIA.parent.mkdir(parents=True, exist_ok=True)
        REFERENCIA.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Referência gravada: {len(resultado)} chamadas em {REFERENCIA}")
        return 0

    esperado = json.loads(REFERENCIA.read_text(encoding="utf-8"))
    for item in esperado:
        if isinstance(item["status"], int) and 200 <= item["status"] < 300:
            item["status"] = "2xx"
    falhas = 0
    for i, (e, r) in enumerate(zip(esperado, resultado)):
        if e != r:
            falhas += 1
            print(f"FALHA [{i}] {e['nome']}")
            print("  esperado:", json.dumps(e, ensure_ascii=False)[:1500])
            print("  obtido:  ", json.dumps(r, ensure_ascii=False)[:1500])
        else:
            print(f"  OK   {e['nome']}")
    if len(esperado) != len(resultado):
        falhas += 1
        print(f"FALHA quantidade de chamadas: esperado {len(esperado)}, obtido {len(resultado)}")
    print(f"\n{len(resultado) - falhas}/{len(resultado)} chamadas iguais à referência.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
