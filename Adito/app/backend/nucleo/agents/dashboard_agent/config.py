from typing import Literal

from pydantic import BaseModel, Field

# Tipos que o chat desenha; são os mesmos do Meu painel, sem `metric_card` e `table`.
CHAT_CHART_TYPES = ("bar", "horizontal_bar", "line", "area", "pie")

# Rótulo comprido (soma das dimensões) ou categorias demais deitam as barras.
LONG_LABEL = 20
MANY_CATEGORIES = 12
# O agente só é chamado entre estes limites; fora deles a regra já decide bem.
AGENT_MIN_ROWS = 3
AGENT_MAX_ROWS = 8


class ChartTypeResponse(BaseModel):
    chart_type: Literal["bar", "horizontal_bar", "pie"] = Field(
        description="Chart type for the answer: bar, horizontal_bar or pie."
    )
    reasoning: str = Field(description="One short sentence in Brazilian Portuguese explaining the choice.")


DASHBOARD_CHART_SYSTEM_PROMPT = """
You choose how a BI answer is drawn in a chat about research and extension projects.
The data has one category column and one numeric column. You only see the question
and a summary of the data shape, never the rows.

Pick one chart type:
- bar: vertical columns. Default for comparing a few categories.
- horizontal_bar: horizontal bars. Rankings ("top", "maiores", "quais mais") or long category names.
- pie: parts of a whole. Only when the question is about the share, proportion, percentage,
  distribution or composition of a total ("participação", "proporção", "percentual",
  "distribuição", "como se divide") and there are few categories.

When in doubt, pick bar. Write the reasoning in Brazilian Portuguese, in one short sentence.
"""
