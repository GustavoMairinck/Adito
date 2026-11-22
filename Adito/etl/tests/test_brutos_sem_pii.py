"""Trava de LGPD sobre os dados reais (US-ETL-02 CA7, US-ETL-03 CA7, NFR06).

Varre `etl/brutos/` e `etl/trabalho/` da máquina da equipe. Falha se qualquer
JSON tiver CPF, e-mail, 11 dígitos seguidos ou coluna pessoal.
"""

from pathlib import Path

import pytest

from adito_etl.pii import varrer

ETL = Path(__file__).resolve().parents[1]


def test_brutos_e_trabalho_sem_pii():
    pastas = [ETL / "brutos", ETL / "trabalho"]
    if not any(p.exists() for p in pastas):
        pytest.skip("ainda não há brutos nesta máquina")
    assert varrer(*pastas) == []
