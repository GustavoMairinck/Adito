"""JSON do `scriptLattes` -> `brutos/lattes/<lattes_id>.json`, só com o permitido.

Entrada: a pasta de saída JSON do `scriptLattes` (arquivos `NN_Nome-Do-Pesquisador_<id16>.json`).
Saída: um arquivo por currículo, com as seções de `colunas.SECOES` e, em
`informacoes_pessoais`, só as chaves de `colunas.INFORMACOES_PESSOAIS`.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from ... import pii
from ...comum import Execucao, brutos_dir, gravar_json
from .colunas import DESCARTADOS_CONHECIDOS, INFORMACOES_PESSOAIS, SECOES

LATTES_ID = re.compile(r"(?<!\d)\d{16}(?!\d)")
_CONTATO = re.compile(r"\s*\b(?:Telefone|Fax|Ramal|Celular)\s*:\s*[\d()\s.+/-]*(?:ramal\s*:?\s*[\d\s]*)?",
                      re.IGNORECASE)


def sem_contato(texto: str) -> str:
    """Tira telefone, fax, ramal e celular do endereço profissional ("... Telefone: (27) 3348 Fax: ...")."""
    return " ".join(_CONTATO.sub(" ", texto).split())


def _sem_chaves_pessoais(v: Any) -> Any:
    """Remove, em qualquer nível, chaves com nome de dado pessoal (cpf, email, telefone...)."""
    if isinstance(v, dict):
        return {k: _sem_chaves_pessoais(x) for k, x in v.items() if not pii.chave_pessoal(k)}
    if isinstance(v, list):
        return [_sem_chaves_pessoais(x) for x in v]
    return v


def filtrar_curriculo(cv: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    """Devolve (currículo filtrado, nomes de seção/campo descartados fora do previsto)."""
    descartados: set[str] = set()
    saida: dict[str, Any] = {}
    for secao, valor in cv.items():
        if secao not in SECOES:
            descartados.add(secao)
            continue
        if secao == "informacoes_pessoais" and isinstance(valor, dict):
            for campo in valor:
                if campo not in INFORMACOES_PESSOAIS and campo not in DESCARTADOS_CONHECIDOS:
                    descartados.add(f"informacoes_pessoais.{campo}")
            valor = {k: v for k, v in valor.items() if k in INFORMACOES_PESSOAIS}
            if isinstance(valor.get("endereco_profissional"), str):
                valor["endereco_profissional"] = sem_contato(valor["endereco_profissional"])
        saida[secao] = _sem_chaves_pessoais(valor)
    return saida, descartados


def id_do_curriculo(arq: Path, cv: dict[str, Any]) -> str | None:
    ident = (cv.get("informacoes_pessoais") or {}).get("id_lattes")
    if isinstance(ident, str) and LATTES_ID.fullmatch(ident.strip()):
        return ident.strip()
    m = LATTES_ID.search(arq.stem)
    return m.group(0) if m else None


def converter_pasta(origem: Path, exe: Execucao, *, apagar: bool = False) -> None:
    destino = brutos_dir("lattes")
    arquivos = sorted(origem.glob("*.json")) if origem.exists() else []
    if not arquivos:
        exe.aviso(f"nenhum JSON do scriptLattes em {origem}")
    avisados: set[str] = set()
    for arq in arquivos:
        try:
            cv = json.loads(arq.read_text(encoding="utf-8"))
            ident = id_do_curriculo(arq, cv)
            if not ident:
                raise ValueError("currículo sem id Lattes de 16 dígitos")
            nome = str((cv.get("informacoes_pessoais") or {}).get("nome_completo") or "")
            if not nome or nome.startswith("[Nome-nao-identificado"):
                raise ValueError(f"currículo {ident} vazio: o scriptLattes não leu o HTML (baixe de novo)")
            filtrado, descartados = filtrar_curriculo(cv)
            for d in sorted(descartados - avisados):
                exe.aviso(f"campo descartado (fora da lista de permitidas): {d}")
            avisados |= descartados
            filtrado, mascarados = pii.sanitizar(filtrado)
            gravar_json(destino / f"{ident}.json", filtrado)
        except Exception as e:
            exe.falha(arq.name, e)
            continue
        exe.conta("curriculos")
        if mascarados:
            exe.conta("valores_mascarados", mascarados)
    if apagar:
        shutil.rmtree(origem, ignore_errors=True)


def converter(origem: Path) -> Execucao:
    """Converte JSON do scriptLattes já gerados (não apaga a origem)."""
    exe = Execucao("lattes", "conversao")
    converter_pasta(origem, exe, apagar=False)
    exe.finalizar()
    return exe
