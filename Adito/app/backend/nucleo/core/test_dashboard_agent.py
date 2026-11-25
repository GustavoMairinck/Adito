"""Agente de painéis: escolha do tipo de gráfico da resposta do chat."""
from __future__ import annotations

import asyncio
import io
import json
import threading
import unittest
from unittest.mock import patch

from agents.dashboard_agent import ChartSuggestion, choose_chart_with_agent, plan_chart, suggest_chart, summarize_rows
from agents.dashboard_agent.agent import explicit_chart_type
from agents.dashboard_agent.config import ChartTypeResponse
from core import db
from core.records import Contexto, Message
from core.tests import AppDbTestCase
from rpc import session

POR_AREA = [
    {"grande_area": "Engenharias", "total": 120},
    {"grande_area": "Ciências Exatas e da Terra", "total": 80},
    {"grande_area": "Ciências Humanas", "total": 45},
    {"grande_area": "Ciências Biológicas", "total": 30},
]

POR_ANO = [
    {"ano": 2021, "total": 30},
    {"ano": 2022, "total": 45},
    {"ano": 2023, "total": 60},
]


class _Structured:
    """Imita `bind_structured_output(...)`: guarda as mensagens e devolve a resposta dada."""

    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.messages = None

    def invoke(self, messages, config=None):
        self.messages = messages
        if self.error:
            raise self.error
        return self.response


class ResumoDosDadosTests(unittest.TestCase):
    def test_mesma_regra_de_eixo_do_front(self) -> None:
        resumo = summarize_rows(POR_ANO)
        # Ano é número, mas é coluna de tempo: vira eixo.
        self.assertEqual(resumo.dimension_keys, ("ano",))
        self.assertEqual(resumo.metric_keys, ("total",))
        self.assertTrue(resumo.time_dimension)

        resumo = summarize_rows([{"codigo": 1, "total": 3}, {"codigo": 2, "total": 4}])
        # Sem coluna de texto nem de tempo: a primeira coluna vira o eixo.
        self.assertEqual(resumo.dimension_keys, ("codigo",))
        self.assertEqual(resumo.metric_keys, ("total",))

    def test_resumo_guarda_contagens_e_tamanhos(self) -> None:
        resumo = summarize_rows(POR_AREA)
        self.assertEqual(resumo.row_count, 4)
        self.assertEqual(resumo.max_label_length, len("Ciências Exatas e da Terra"))
        self.assertAlmostEqual(resumo.top_share, 120 / 275)
        self.assertTrue(resumo.can_use_pie)

        com_negativo = summarize_rows([{"area": "A", "saldo": 3}, {"area": "B", "saldo": -1}])
        self.assertTrue(com_negativo.has_negative)
        self.assertFalse(com_negativo.can_use_pie)
        self.assertIsNone(com_negativo.top_share)

        duas_series = summarize_rows([{**row, "valor": row["total"] * 10} for row in POR_AREA])
        self.assertFalse(duas_series.can_use_pie)

    def test_escalar_e_vazio_nao_viram_grafico(self) -> None:
        self.assertFalse(summarize_rows([{"total": 236}]).chartable)
        self.assertFalse(summarize_rows([]).chartable)
        self.assertFalse(summarize_rows(None).chartable)
        self.assertFalse(summarize_rows([{"nome": "A"}, {"nome": "B"}]).chartable)


class PedidoExplicitoTests(unittest.TestCase):
    def test_reconhece_o_tipo_pedido(self) -> None:
        casos = {
            "Mostre os projetos por área em pizza": "pie",
            "quero um gráfico de setores": "pie",
            "Projetos por campus em barras horizontais": "horizontal_bar",
            "bolsas por ano em gráfico de linhas": "line",
            "bolsas por ano, em linha.": "line",
            "mostra a linha do tempo dos projetos": "line",
            "bolsas por ano em gráfico de área": "area",
            "projetos por área em colunas": "bar",
            "Faça um gráfico de barras": "bar",
        }
        for pergunta, esperado in casos.items():
            with self.subTest(pergunta=pergunta):
                self.assertEqual(explicit_chart_type(pergunta), esperado)

    def test_nao_confunde_palavras_do_dominio(self) -> None:
        for pergunta in (
            "Quantos projetos existem por grande área?",
            "Projetos da área de Engenharias",
            "Quantos grupos estão em linha de pesquisa de robótica?",
            "Quais as linhas de pesquisa mais comuns?",
            "Quantas bolsas por modalidade?",
        ):
            with self.subTest(pergunta=pergunta):
                self.assertIsNone(explicit_chart_type(pergunta))


class PlanoSemLLMTests(unittest.TestCase):
    def test_regra_decide_os_casos_obvios(self) -> None:
        self.assertEqual(plan_chart("projetos por ano", POR_ANO).suggestion(), ChartSuggestion("line", "regra", "Formato dos dados decide."))
        # Duas linhas: nada a escolher.
        plano = plan_chart("projetos por modalidade", [{"modalidade": "PIBIC", "total": 3}, {"modalidade": "PIBITI", "total": 2}])
        self.assertEqual((plano.chart_type, plano.needs_agent), ("bar", False))
        # Muitas categorias deitam as barras.
        muitas = [{"campus": f"Campus {i:02d}", "total": i} for i in range(1, 15)]
        plano = plan_chart("projetos por campus", muitas)
        self.assertEqual((plano.chart_type, plano.needs_agent), ("horizontal_bar", False))
        # Duas séries: sem pizza, regra decide.
        plano = plan_chart("projetos e valor por área", [{**row, "valor": 1} for row in POR_AREA])
        self.assertEqual((plano.chart_type, plano.needs_agent), ("horizontal_bar", False))

    def test_pedido_vence_a_regra_mas_pizza_invalida_cai_na_regra(self) -> None:
        plano = plan_chart("projetos por ano em pizza", POR_ANO)
        self.assertEqual((plano.chart_type, plano.source), ("pie", "pedido"))

        com_negativo = [{"area": "A", "saldo": 3}, {"area": "B", "saldo": -1}, {"area": "C", "saldo": 2}]
        plano = plan_chart("saldo por área em pizza", com_negativo)
        self.assertEqual((plano.chart_type, plano.source, plano.needs_agent), ("bar", "regra", False))

    def test_categoria_com_uma_serie_e_poucas_linhas_vai_para_o_agente(self) -> None:
        plano = plan_chart("Quantos projetos por grande área?", POR_AREA)
        self.assertTrue(plano.needs_agent)
        # Se o agente falhar, vale a regra: rótulo comprido deita as barras.
        self.assertEqual((plano.chart_type, plano.source), ("horizontal_bar", "regra"))

    def test_sem_grafico_nao_chama_nada(self) -> None:
        with patch("agents.dashboard_agent.agent.get_chat_llm", side_effect=AssertionError("não devia chamar o LLM")):
            self.assertEqual(suggest_chart("Quantos projetos?", [{"total": 236}]).chart_type, None)
            self.assertEqual(suggest_chart("projetos por ano", POR_ANO).chart_type, "line")
            self.assertEqual(suggest_chart("projetos por área em pizza", POR_AREA).chart_type, "pie")


class AgenteTests(unittest.TestCase):
    def _escolher(self, structured: _Structured, pergunta="Qual a participação de cada área no total?"):
        plano = plan_chart(pergunta, POR_AREA)
        with (
            patch("agents.dashboard_agent.agent.get_chat_llm", return_value=object()),
            patch("agents.dashboard_agent.agent.bind_structured_output", return_value=structured),
        ):
            return choose_chart_with_agent(pergunta, plano)

    def test_usa_a_escolha_do_agente(self) -> None:
        structured = _Structured(ChartTypeResponse(chart_type="pie", reasoning="A pergunta pede a participação no total."))
        sugestao = self._escolher(structured)
        self.assertEqual((sugestao.chart_type, sugestao.source), ("pie", "agente"))

    def test_nao_manda_as_linhas_ao_llm(self) -> None:
        structured = _Structured(ChartTypeResponse(chart_type="bar", reasoning="Comparação simples."))
        self._escolher(structured)
        prompt = "\n".join(str(message.content) for message in structured.messages)
        for row in POR_AREA:
            self.assertNotIn(row["grande_area"], prompt)
            self.assertNotIn(str(row["total"]), prompt.split("Resumo dos dados:")[1].split("categorias:")[0])
        self.assertIn("categorias: 4", prompt)
        self.assertIn("grande_area", prompt)

    def test_falha_ou_resposta_invalida_devolvem_a_regra(self) -> None:
        sugestao = self._escolher(_Structured(error=RuntimeError("cota esgotada")))
        self.assertEqual((sugestao.chart_type, sugestao.source), ("horizontal_bar", "regra"))

        invalida = _Structured(ChartTypeResponse.model_construct(chart_type="line", reasoning="?"))
        sugestao = self._escolher(invalida)
        self.assertEqual((sugestao.chart_type, sugestao.source), ("horizontal_bar", "regra"))


class ChatComAgenteDePaineisTests(AppDbTestCase):
    def test_chat_stream_envia_e_grava_o_tipo_de_grafico(self) -> None:
        from agents.orchestrator.graph import close_graph
        from agents.orchestrator.models import AgentCall, RouterDecision
        from rpc.server import Server

        _, tenant = session.current()
        ctx = Contexto(tenant_id=tenant.id, slug="ctx-grafico", name="Gráfico", views=[]).insert()

        class _Router:
            async def ainvoke(self, messages):
                return RouterDecision(calls=[AgentCall(intent="bi_agent", delegation_instruction="Projetos por área")])

        class _BITool:
            name = "bi_agent"
            description = "dados"

            async def ainvoke(self, args):
                return json.dumps({
                    "final_content": "Engenharias lidera.",
                    "text_response": "Engenharias lidera.",
                    "sql_used": "SELECT grande_area, COUNT(*) AS total FROM v GROUP BY grande_area",
                    "data_rows": POR_AREA,
                    "field_formats": {"grande_area": "text", "total": "integer"},
                    "type": "analysis",
                })

        perguntas_ao_agente: list[str] = []

        def fake_choose(question, plan, llm_model=None):
            perguntas_ao_agente.append(question)
            return ChartSuggestion("pie", "agente", "Participação no total.")

        async def scenario():
            out = io.StringIO()
            server = Server(out)
            with (
                patch("rpc.chat.llm_configured", return_value=True),
                patch("rpc.chat.local_tools", return_value=[_BITool()]),
                patch("agents.orchestrator.router.get_chat_llm", return_value=object()),
                patch("agents.orchestrator.router.bind_structured_output", return_value=_Router()),
                patch("rpc.chat.choose_chart_with_agent", side_effect=fake_choose),
            ):
                server.handle({
                    "id": 401,
                    "method": "chat.stream",
                    "params": {"question": "Qual a participação de cada área?", "contexto_id": ctx.id},
                })
                await asyncio.gather(*list(server.tasks.values()), return_exceptions=True)
            await close_graph()
            return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]

        lines = asyncio.run(scenario())
        eventos = [m for m in lines if m.get("id") == 401 and m.get("event")]
        status = [m["data"].get("message") for m in eventos if m["event"] == "status"]
        self.assertIn("Escolhendo o gráfico...", status)
        result = next(m["data"] for m in eventos if m["event"] == "result")
        self.assertEqual((result["chart_type"], result["chart_source"]), ("pie", "agente"))
        self.assertEqual(perguntas_ao_agente, ["Qual a participação de cada área?"])

        salva = Message.first("id = ?", [db.to_db_id(result["message_id"])])
        self.assertEqual(salva.metadata["chart_type"], "pie")
        self.assertEqual(salva.metadata["chart_source"], "agente")

    def test_persistencia_descarta_tipo_fora_da_lista(self) -> None:
        from rpc.chat import persist_assistant_response, prepare_conversation

        _, tenant = session.current()
        ctx = Contexto(tenant_id=tenant.id, slug="ctx-grafico-invalido", name="Gráfico", views=[]).insert()
        conv, user_msg = prepare_conversation("Pergunta", None, ctx.id)
        payload = persist_assistant_response(
            conv, user_msg, "Pergunta",
            {"answer": "Resposta", "sql": "SELECT 1", "data": POR_AREA, "valid": True,
             "chart_type": "metric_card", "chart_source": "agente"},
            cancel_event=threading.Event(),
        )
        self.assertIsNone(payload["chart_type"])
        self.assertIsNone(Message.first("id = ?", [db.to_db_id(payload["message_id"])]).metadata["chart_type"])


if __name__ == "__main__":
    unittest.main()
