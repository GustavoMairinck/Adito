"""Trava de dado pessoal (BR01): só o nome pode ficar nos arquivos do ETL.

- `sanitizar` mascara CPF, e-mail e sequências de 11 dígitos em textos livres
  (ex.: um e-mail no resumo de uma ação, ou "Nome (email)" na lista de líderes).
- `auditar` é a última barreira: recusa gravar JSON com CPF, e-mail, 11 dígitos
  seguidos ou chave de coluna pessoal.
- `varrer` audita todos os JSON de uma pasta (usado no teste e no comando
  `adito-etl verificar-pii`).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

_RE_CPF = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_RE_11DIG = re.compile(r"(?<!\d)\d{11}(?!\d)")
_RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_RE_EMAIL_PARENTESES = re.compile(r"\s*\([^()]*@[^()]*\)")
_RE_CHAVE_JSON = re.compile(r'"((?:[^"\\]|\\.)*)"\s*:')

# Pedaços de nome de coluna que indicam dado pessoal (comparados sem acento,
# minúsculos e sem pontuação).
_CHAVES_PESSOAIS = ("cpf", "email", "celular", "telefone", "nascimento", "nasc", "rg")


class PIIEncontrada(RuntimeError):
    """Dado pessoal além do nome encontrado onde não pode estar."""


def _chave_normalizada(chave: str) -> str:
    s = unicodedata.normalize("NFKD", chave)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def chave_pessoal(chave: str) -> bool:
    """True se o nome da coluna indica dado pessoal (CPF, e-mail, celular...)."""
    k = _chave_normalizada(chave)
    return any(k == p or (len(p) > 2 and p in k) for p in _CHAVES_PESSOAIS)


def mascarar(texto: str) -> tuple[str, int]:
    """Remove/mascara dado pessoal de um texto livre. Devolve (texto, nº de trocas)."""
    total = 0
    texto, n = _RE_EMAIL_PARENTESES.subn("", texto)
    total += n
    texto, n = _RE_EMAIL.subn("[e-mail removido]", texto)
    total += n
    texto, n = _RE_CPF.subn("[cpf removido]", texto)
    total += n
    texto, n = _RE_11DIG.subn("[número removido]", texto)
    total += n
    return texto, total


def sanitizar(dados: Any) -> tuple[Any, int]:
    """Aplica `mascarar` em todas as strings de uma estrutura JSON."""
    if isinstance(dados, str):
        return mascarar(dados)
    if isinstance(dados, dict):
        total, out = 0, {}
        for k, v in dados.items():
            out[k], n = sanitizar(v)
            total += n
        return out, total
    if isinstance(dados, list):
        total, lista = 0, []
        for v in dados:
            novo, n = sanitizar(v)
            lista.append(novo)
            total += n
        return lista, total
    return dados, 0


def auditar(texto: str, origem: str = "") -> None:
    """Levanta `PIIEncontrada` se o JSON tiver CPF, e-mail, 11 dígitos ou chave pessoal."""
    if _RE_CPF.search(texto):
        raise PIIEncontrada(f"CPF encontrado em {origem}")
    if _RE_EMAIL.search(texto):
        raise PIIEncontrada(f"e-mail encontrado em {origem}")
    if _RE_11DIG.search(texto):
        raise PIIEncontrada(f"sequência de 11 dígitos (possível CPF/celular) em {origem}")
    for chave in _RE_CHAVE_JSON.findall(texto):
        if chave_pessoal(chave):
            raise PIIEncontrada(f"coluna pessoal '{chave}' em {origem}")


def varrer(*pastas: Path) -> list[str]:
    """Audita todos os .json das pastas. Devolve a lista de problemas (vazia = ok)."""
    problemas: list[str] = []
    for pasta in pastas:
        if not pasta.exists():
            continue
        for arq in sorted(pasta.rglob("*.json")):
            try:
                auditar(arq.read_text(encoding="utf-8"), str(arq))
            except PIIEncontrada as e:
                problemas.append(str(e))
    return problemas
