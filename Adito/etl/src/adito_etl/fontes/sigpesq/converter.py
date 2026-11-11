"""XLSX do SigPesq -> JSON em `brutos/sigpesq/<relatorio>/`, só com colunas permitidas.

Entrada: a pasta que a `sigpesq-agent` preenche
    research_group/<arquivo>.xlsx
    research_projects/<arquivo>.xlsx
    advisorships/<ano>/<arquivo>.xlsx
Saída:
    brutos/sigpesq/grupos/relatorio.json
    brutos/sigpesq/projetos/relatorio.json
    brutos/sigpesq/orientacoes/<ano>.json
Cada JSON: {"arquivo_origem", "colunas", "linhas": [{coluna: valor}]}.
"""

from __future__ import annotations

import shutil
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ... import pii
from ...comum import Execucao, brutos_dir, filtrar_colunas, gravar_json
from .colunas import RELATORIOS


def _valor(v: Any) -> Any:
    if isinstance(v, (datetime, date, time)):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def ler_xlsx(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Primeira planilha: cabeçalho = primeira linha com 3+ células preenchidas."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        linhas_brutas = wb.worksheets[0].iter_rows(values_only=True)
        cabecalho: list[str] | None = None
        linhas: list[dict[str, Any]] = []
        for row in linhas_brutas:
            if cabecalho is None:
                if row and sum(1 for c in row if c not in (None, "")) >= 3:
                    cabecalho = [str(c).strip() if c is not None else "" for c in row]
                continue
            if not row or all(c in (None, "") for c in row):
                continue
            linhas.append({cabecalho[i]: _valor(row[i]) if i < len(row) else None
                           for i in range(len(cabecalho)) if cabecalho[i]})
        return [c for c in (cabecalho or []) if c], linhas
    finally:
        wb.close()


def converter_pasta(origem: Path, exe: Execucao, *, apagar: bool = False) -> None:
    """Converte todos os relatórios encontrados em `origem` para JSON filtrado."""
    destino_base = brutos_dir("sigpesq")
    for rel in RELATORIOS:
        pasta = origem / rel.pasta
        arquivos = sorted(pasta.rglob("*.xlsx")) if pasta.exists() else []
        if not arquivos:
            exe.aviso(f"relatório {rel.pasta} ausente em {origem.name}")
            continue
        for arq in arquivos:
            partes = arq.relative_to(pasta).parts
            nome_saida = f"{partes[0]}.json" if len(partes) > 1 else "relatorio.json"
            destino = destino_base / rel.nome / nome_saida
            try:
                colunas, linhas = ler_xlsx(arq)
                filtradas, novas = filtrar_colunas(linhas, rel.permitidas)
                for col in novas:
                    exe.aviso(f"{rel.nome}: coluna descartada (fora da lista de permitidas): {col}")
                filtradas, mascarados = pii.sanitizar(filtradas)
                gravar_json(destino, {
                    "arquivo_origem": arq.name,
                    "colunas": [c for c in colunas if c in rel.permitidas],
                    "linhas": filtradas,
                })
            except Exception as e:
                exe.falha(f"{rel.nome}/{nome_saida}", e)
                continue
            exe.conta(f"{rel.nome}_linhas", len(filtradas))
            if mascarados:
                exe.conta("valores_mascarados", mascarados)
    if apagar:
        shutil.rmtree(origem, ignore_errors=True)


def converter(origem: Path) -> Execucao:
    """Converte uma pasta de XLSX já baixada (não apaga a origem)."""
    exe = Execucao("sigpesq", "conversao")
    converter_pasta(origem, exe, apagar=False)
    exe.finalizar()
    return exe
