"""Formas normalizadas de nome (BR02), portadas do horizon_etl.

Origem: `horizon_etl/src/core/logic/person_identity.py` (`normalize_participant_name`,
`is_junk_name`) e as regras de `person_matcher.match_or_create` com
`strict_match=True`, que é como todos os fluxos do horizon chamam (commit 13a1cec).

O horizon considera dois nomes a mesma pessoa quando coincide qualquer uma
destas três formas (todas por igualdade exata, nunca por semelhança):

1. `forma_canonica`: sem acento, minúsculo, pontuação e hífen viram espaço,
   espaços únicos. "Maria-José D'Ávila" -> "maria jose d avila".
2. `forma_invariante`: a canônica sem partículas de sobrenome
   (da, de, di, do, dos, das, du, del, dela, e, y) e com "Jr" escrito "junior".
   "Tiago Sérgio dos Exemplo Jr." == "Tiago Sergio Exemplo Junior".
3. `forma_ordenada`: as palavras da canônica em ordem alfabética
   (equivale ao `token_sort_ratio == 100` do horizon). "Silva, João" == "João Silva".

Filho, Neto e Sobrinho continuam distintos (separam gerações).
"""

from __future__ import annotations

import unicodedata

PARTICULAS = frozenset({"da", "de", "di", "do", "dos", "das", "du", "del", "dela", "e", "y"})
TITULOS = frozenset({"dr", "dra", "prof", "msc", "phd", "me", "ma", "bel", "esp", "eng", "sr", "sra"})
_SUFIXOS = {"jr": "junior"}


def _tokens(nome: object) -> list[str]:
    if nome is None:
        return []
    s = unicodedata.normalize("NFD", str(nome))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return s.lower().split()


def forma_canonica(nome: object) -> str:
    return " ".join(_tokens(nome))


def forma_invariante(nome: object) -> str:
    return " ".join(_SUFIXOS.get(t, t) for t in _tokens(nome) if t not in PARTICULAS)


def forma_ordenada(nome: object) -> str:
    return " ".join(sorted(_tokens(nome)))


def nome_implausivel(nome: object) -> bool:
    """Nome que não pode ser ligado a nada: menos de duas palavras fora os títulos
    ("Dr", "Prof. Dra", "Maria"). Igual ao `is_junk_name` do horizon."""
    return len([t for t in _tokens(nome) if t not in TITULOS]) < 2


# Nome usado pelo resto do pacote para a forma de exibição/comparação simples.
normalizar_nome = forma_canonica
