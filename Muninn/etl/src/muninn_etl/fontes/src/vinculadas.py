"""(Copiado do SRCEtl: src_etl/etl/vinculadas.py, só a busca.) Vínculos ação-mãe -> filhas.

O campo texto "Ação vinculante" do detalhe é incompleto. A fonte correta é
`consulta-acao-vinculada.xhtml?acao_vinculante=<acao_id>`, que lista as ações
vinculadas a uma ação-mãe.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .detalhe import BASE

VINC_URL = BASE + "consulta-acao-vinculada.xhtml?acao_vinculante="


def parse_vinculadas(html: str) -> list[dict[str, str]]:
    """Lê a tabela de ações vinculadas (processo, natureza, tipo, título)."""
    soup = BeautifulSoup(html, "html.parser")
    filhas = []
    for tr in soup.select("table tbody tr"):
        c = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if len(c) >= 4 and c[0] and "nenhum" not in c[0].lower():
            filhas.append({"processo": c[0], "natureza": c[1], "tipo": c[2], "titulo": c[3]})
    return filhas


def fetch_vinculadas(acao_id: str, client: httpx.Client) -> list[dict[str, str]]:
    """Devolve as ações vinculadas (filhas) de uma ação-mãe, pela fonte oficial."""
    r = client.get(f"{VINC_URL}{acao_id}", timeout=30)
    r.raise_for_status()
    return parse_vinculadas(r.text)
