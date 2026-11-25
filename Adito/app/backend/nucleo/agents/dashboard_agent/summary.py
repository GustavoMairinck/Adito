"""Resumo do formato de um resultado, para decidir o gráfico sem olhar valor por valor.

Mesma regra de eixo e séries do front (`src/common/utils/chartKeys.ts`): coluna de tempo ou de
texto vira eixo (dimensão); as outras colunas com número viram séries (métricas). O resumo só
guarda contagens e tamanhos; nenhum valor das linhas vai para o LLM.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

TIME_KEY = re.compile(
    r"^(ano|anos|mes|m[eê]s|dia|data|trimestre|semestre|periodo|per[ií]odo|year|month|quarter|date)$"
    r"|^(ano|mes|data|trimestre|semestre|year|month)_|_(ano|mes|data|year|month)$",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def parse_strict_number(value: Any) -> float | None:
    """Número de verdade: "2024" e 12.5 sim; "2024-01-01", "PIBIC", vazio e booleano não."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip()
    if not text or not _NUMBER.match(text):
        return None
    number = float(text)
    return number if math.isfinite(number) else None


def is_time_key(key: str) -> bool:
    return bool(TIME_KEY.search(str(key)))


def chart_keys(rows: list[dict]) -> tuple[list[str], list[str]]:
    """(dimensões, métricas) do resultado, como o `chartKeys` do front."""
    if not rows:
        return [], []
    keys = list(rows[0].keys())

    def has_text(key: str) -> bool:
        return any(
            row.get(key) not in (None, "") and parse_strict_number(row.get(key)) is None
            for row in rows
        )

    def has_number(key: str) -> bool:
        return any(parse_strict_number(row.get(key)) is not None for row in rows)

    dimensions = [key for key in keys if is_time_key(key) or has_text(key)]
    if not dimensions and len(keys) > 1:
        dimensions = [keys[0]]
    metrics = [key for key in keys if key not in dimensions and has_number(key)]
    return dimensions, metrics


def _label(row: dict, dimensions: Iterable[str]) -> str:
    values = [row.get(key) for key in dimensions]
    return " · ".join(str(value) for value in values if value not in (None, ""))


@dataclass(frozen=True)
class DataSummary:
    row_count: int
    dimension_keys: tuple[str, ...]
    metric_keys: tuple[str, ...]
    has_negative: bool
    has_positive: bool
    max_label_length: int
    # Fatia da maior categoria no total da primeira série (0 a 1), quando faz sentido.
    top_share: float | None

    @property
    def chartable(self) -> bool:
        """O chat só desenha gráfico com alguma série e mais de uma linha."""
        return bool(self.metric_keys) and self.row_count > 1

    @property
    def time_dimension(self) -> bool:
        return len(self.dimension_keys) == 1 and is_time_key(self.dimension_keys[0])

    @property
    def can_use_pie(self) -> bool:
        """Pizza: uma série só, sem negativos e com algum valor positivo (`canUsePie` do front)."""
        return len(self.metric_keys) == 1 and not self.has_negative and self.has_positive


def summarize_rows(rows: list[dict] | None) -> DataSummary:
    rows = [row for row in (rows or []) if isinstance(row, dict)]
    dimensions, metrics = chart_keys(rows)
    values = [
        number
        for row in rows
        for key in metrics
        if (number := parse_strict_number(row.get(key))) is not None
    ]
    top_share = None
    if len(metrics) == 1:
        first = [parse_strict_number(row.get(metrics[0])) or 0.0 for row in rows]
        total = sum(first)
        if total > 0 and all(value >= 0 for value in first):
            top_share = max(first) / total
    return DataSummary(
        row_count=len(rows),
        dimension_keys=tuple(dimensions),
        metric_keys=tuple(metrics),
        has_negative=any(value < 0 for value in values),
        has_positive=any(value > 0 for value in values),
        max_label_length=max((len(_label(row, dimensions)) for row in rows), default=0),
        top_share=top_share,
    )
