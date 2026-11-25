"""Agente de painéis: escolhe como desenhar o resultado de uma pergunta (tipo de gráfico).

Pensado para crescer junto com o Meu painel (ordenação, limite, título e, no futuro, montar
painéis inteiros). Hoje só escolhe o tipo de gráfico da resposta do chat.
"""
from .agent import ChartPlan, ChartSuggestion, choose_chart_with_agent, plan_chart, suggest_chart
from .summary import DataSummary, summarize_rows

__all__ = [
    "ChartPlan",
    "ChartSuggestion",
    "DataSummary",
    "choose_chart_with_agent",
    "plan_chart",
    "suggest_chart",
    "summarize_rows",
]
