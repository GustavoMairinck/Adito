"""Escolha do tipo de gráfico de uma resposta.

Três fontes, nesta ordem:
1. pedido: a pergunta diz o tipo ("em pizza", "gráfico de linhas"). Sem LLM.
2. regra: o formato dos dados decide (série no tempo vira linhas, rótulo comprido deita as barras…).
   Sem LLM.
3. agente: só quando a regra não decide bem, ou seja, uma categoria e uma série de 3 a 8 linhas,
   em que barras, barras deitadas e pizza fazem sentido. Aí a intenção da pergunta decide, numa
   chamada curta ao LLM com só o resumo dos dados.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from agents.bi_agent.cancellation import check_cancelled
from agents.config import bind_structured_output, get_chat_llm, langfuse_callbacks
from core.rich_logging import log_error, log_info

from .config import (
    AGENT_MAX_ROWS,
    AGENT_MIN_ROWS,
    CHAT_CHART_TYPES,
    DASHBOARD_CHART_SYSTEM_PROMPT,
    LONG_LABEL,
    MANY_CATEGORIES,
    ChartTypeResponse,
)
from .summary import DataSummary, summarize_rows

SOURCE_REQUEST = "pedido"
SOURCE_RULE = "regra"
SOURCE_AGENT = "agente"

AGENT_OPTIONS = ("bar", "horizontal_bar", "pie")

# A ordem importa: "barras horizontais" é pedido de barra deitada, não de barra.
_EXPLICIT = (
    ("horizontal_bar", re.compile(r"barras?\s+(deitadas?|horizonta(l|is))|\bhorizonta(l|is)\b")),
    ("pie", re.compile(r"\b(pizza|torta|rosca)\b|grafico\s+de\s+setor(es)?\b|\bem\s+setores\b")),
    ("area", re.compile(r"grafico\s+(de|em)\s+area\b|\bem\s+area\s*([?.!,;]|$)")),
    ("line", re.compile(
        r"grafico\s+(de|em)\s+linhas?\b|\b(em|como)\s+linhas?\s*([?.!,;]|$)|\blinha\s+do\s+tempo\b"
    )),
    ("bar", re.compile(r"grafico\s+(de|em)\s+(barras?|colunas?)\b|\bem\s+(barras?|colunas?)\b")),
)


@dataclass(frozen=True)
class ChartSuggestion:
    chart_type: str | None
    source: str | None
    reason: str = ""


@dataclass(frozen=True)
class ChartPlan:
    """Decisão sem LLM. Se `needs_agent`, `chart_type` é o que vale caso o agente falhe."""

    summary: DataSummary
    chart_type: str | None
    source: str | None
    reason: str
    needs_agent: bool = False

    def suggestion(self) -> ChartSuggestion:
        return ChartSuggestion(self.chart_type, self.source, self.reason)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def explicit_chart_type(question: str) -> str | None:
    """Tipo pedido com todas as letras na pergunta. Cuidado com "grande área" e "linha de pesquisa"."""
    text = _normalize(question)
    for chart_type, pattern in _EXPLICIT:
        if pattern.search(text):
            return chart_type
    return None


def rule_chart_type(summary: DataSummary) -> str:
    if summary.time_dimension and summary.row_count >= 3:
        return "line"
    if summary.max_label_length > LONG_LABEL or summary.row_count > MANY_CATEGORIES:
        return "horizontal_bar"
    return "bar"


def _is_ambiguous(summary: DataSummary) -> bool:
    return (
        len(summary.dimension_keys) == 1
        and not summary.time_dimension
        and summary.can_use_pie
        and AGENT_MIN_ROWS <= summary.row_count <= AGENT_MAX_ROWS
    )


def plan_chart(question: str, rows: list[dict] | None) -> ChartPlan:
    summary = summarize_rows(rows)
    if not summary.chartable:
        return ChartPlan(summary, None, None, "Resultado sem gráfico.")

    requested = explicit_chart_type(question)
    if requested and (requested != "pie" or summary.can_use_pie):
        return ChartPlan(summary, requested, SOURCE_REQUEST, "Tipo pedido na pergunta.")

    chart_type = rule_chart_type(summary)
    if _is_ambiguous(summary):
        return ChartPlan(summary, chart_type, SOURCE_RULE, "Regra usada porque o agente não respondeu.", needs_agent=True)
    return ChartPlan(summary, chart_type, SOURCE_RULE, "Formato dos dados decide.")


def _agent_prompt(question: str, summary: DataSummary) -> str:
    share = f"{summary.top_share:.0%}" if summary.top_share is not None else "desconhecida"
    return (
        f"Pergunta: {question}\n\n"
        "Resumo dos dados:\n"
        f"- coluna de categoria: {summary.dimension_keys[0]}\n"
        f"- coluna numérica: {summary.metric_keys[0]}\n"
        f"- categorias: {summary.row_count}\n"
        f"- maior rótulo de categoria: {summary.max_label_length} caracteres\n"
        f"- fatia da maior categoria no total: {share}\n"
    )


def choose_chart_with_agent(question: str, plan: ChartPlan, llm_model=None) -> ChartSuggestion:
    """Chamada curta ao LLM para os casos ambíguos. Qualquer falha devolve a regra."""
    if not plan.needs_agent:
        return plan.suggestion()
    check_cancelled()
    try:
        model = llm_model if llm_model is not None else get_chat_llm(temperature=0.0)
        structured = bind_structured_output(model, ChartTypeResponse)
        response = structured.invoke(
            [
                SystemMessage(content=DASHBOARD_CHART_SYSTEM_PROMPT),
                HumanMessage(content=_agent_prompt(question, plan.summary)),
            ],
            config={"callbacks": langfuse_callbacks(), "run_name": "dashboard_chart_type"},
        )
    except Exception as exc:  # noqa: BLE001 - o gráfico nunca derruba a resposta
        log_error("dashboard_agent", f"Falha ao escolher o gráfico: {exc}")
        return plan.suggestion()
    check_cancelled()

    chart_type = getattr(response, "chart_type", None)
    if chart_type not in AGENT_OPTIONS or (chart_type == "pie" and not plan.summary.can_use_pie):
        log_error("dashboard_agent", f"Tipo inválido do agente: {chart_type!r}; usando a regra.")
        return plan.suggestion()
    reason = (getattr(response, "reasoning", "") or "").strip()
    log_info("dashboard_agent", f"tipo={chart_type} motivo={reason[:120]!r}")
    return ChartSuggestion(chart_type, SOURCE_AGENT, reason)


def suggest_chart(question: str, rows: list[dict] | None, llm_model=None) -> ChartSuggestion:
    """Plano sem LLM e, só se for ambíguo, a escolha do agente."""
    plan = plan_chart(question, rows)
    if plan.needs_agent:
        return choose_chart_with_agent(question, plan, llm_model)
    return plan.suggestion()


def is_chat_chart_type(value: object) -> bool:
    return value in CHAT_CHART_TYPES
