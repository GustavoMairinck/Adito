"""Agência financiadora de cada orientação, lida do HTML do currículo.

O Lattes escreve cada orientação como
    "Aluno. Título. 2026. Dissertação (Mestrado em X) - Instituição, Agência. Orientador: Fulano."
e, sem agência, "... - Instituição, . Orientador: ...". O `scriptLattes` corta a
instituição na primeira vírgula e perde a agência; aqui ela é lida do HTML que o
download deixa em `trabalho/lattes_cache/<id>` e gravada como `financiador` em
cada orientação do JSON, antes do HTML ser apagado.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup

# Nomes de instituição que contêm vírgula (o pedaço depois dela não é agência).
_SEM_AGENCIA = {"instituto federal de educacao ciencia e tecnologia do espirito santo",
                "ciencia e tecnologia do espirito santo"}
_FIM = re.compile(r"\s*\.?\s*\(?\s*(orientador|coorientador|co-orientador|supervisor)\b", re.I)


def _forma(s: Any) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in s.lower()).split())


def itens_de_orientacao(html: str) -> list[str]:
    """Texto de cada orientação (em andamento e concluídas), com espaços normalizados."""
    inicio = min((i for i in (html.find('name="Orientacoesemandamento"'), html.find('name="Orientacoesconcluidas"'))
                  if i >= 0), default=-1)
    if inicio < 0:
        return []
    fim = html.find('class="title-wrapper"', inicio)
    trecho = html[inicio:fim if fim > 0 else len(html)]
    sopa = BeautifulSoup(trecho, "html.parser")
    return [" ".join(s.get_text(" ").split()) for s in sopa.select("div.layout-cell-11 span.transform")]


def agencia(item: str) -> str | None:
    """'... - Instituição, Agência. Orientador: X.' -> 'Agência' (None se vazia)."""
    m = _FIM.search(item)
    corpo = item[:m.start()] if m else item
    if " - " not in corpo:
        return None
    inst_ag = corpo.rsplit(" - ", 1)[1].strip()
    # sem "Orientador:", o nome do professor vem depois: "..., CAPES. Fulano."
    inst_ag = re.split(r"\.\s+", inst_ag, maxsplit=1)[0].strip().rstrip(".").strip()
    if "," not in inst_ag:
        return None
    if _forma(inst_ag) in _SEM_AGENCIA:  # só o nome completo do Ifes, que tem vírgula
        return None
    ag = inst_ag.rsplit(",", 1)[1].strip(" .")
    if not ag or _pedaco_do_ifes(ag):
        return None
    return ag


def _pedaco_do_ifes(ag: str) -> bool:
    """'Ciência e Tecnologia do' / '... do Espírito Santo': resto do nome do Ifes, não agência."""
    f = _forma(ag)
    return f in _SEM_AGENCIA or "ciencia e tecnologia do espirito santo".startswith(f)


def enriquecer(cv: dict, html: str) -> int:
    """Grava `financiador` em cada orientação do JSON cujo título aparece no HTML. Devolve quantas."""
    itens = [(_forma(t), agencia(t)) for t in itens_de_orientacao(html)]
    n = 0
    for situacao in ("em_andamento", "concluidas"):
        for lista in ((cv.get("orientacoes") or {}).get(situacao) or {}).values():
            for o in lista or []:
                titulo = _forma(o.get("titulo"))
                if not titulo:
                    continue
                ag = next((a for t, a in itens if titulo in t), None)
                if ag:
                    o["financiador"] = ag
                    n += 1
    return n
