#!/usr/bin/env python3
"""Gera Muninn/etl/entradas/lattes.csv a partir do mapeamento ROSTER_IDS do repositório.

Uso:
    python3 Muninn/scripts/gerar_lista_lattes.py
    python3 Muninn/scripts/gerar_lista_lattes.py --saida /caminho/lattes.csv [--fonte /caminho/fonte.py] [--force]

Regras:
- Nunca sobrescreve um lattes.csv já existente sem --force (preserva listas customizadas).
- Extrai ROSTER_IDS via ast.parse (sem importar ou executar módulos do código legado).
- Se o arquivo fonte não existir, falha com instrução clara do caminho e formato CSV esperado.
"""
from __future__ import annotations

import argparse
import ast
import csv
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_FONTE = ROOT_DIR / "Etls" / "Horizon" / "Etl" / "src" / "scripts" / "generate_docentes_executive.py"
DEFAULT_SAIDA = ROOT_DIR / "Muninn" / "etl" / "entradas" / "lattes.csv"
LATTES_ID_RE = re.compile(r"^\d{16}$")


def extrair_roster_ids(fonte: Path) -> list[tuple[str, str]]:
    """Extrai pares (nome, lattes_id) do literal ROSTER_IDS em um arquivo Python usando AST."""
    tree = ast.parse(fonte.read_text(encoding="utf-8"), filename=str(fonte))
    roster: dict[str, str] | None = None

    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "ROSTER_IDS":
            if node.value is not None:
                roster = ast.literal_eval(node.value)
                break
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ROSTER_IDS":
                    roster = ast.literal_eval(node.value)
                    break
            if roster is not None:
                break

    if not isinstance(roster, dict) or not roster:
        raise ValueError(f"Mapeamento ROSTER_IDS não encontrado ou vazio em '{fonte}'.")

    vistos: set[str] = set()
    registros: list[tuple[str, str]] = []
    for nome_raw, id_raw in roster.items():
        nome = str(nome_raw).strip()
        lattes_id = str(id_raw).strip()
        if not nome or not LATTES_ID_RE.fullmatch(lattes_id):
            continue
        if lattes_id not in vistos:
            vistos.add(lattes_id)
            registros.append((nome, lattes_id))

    if not registros:
        raise ValueError(f"Nenhum par (nome, lattes_id de 16 dígitos) válido encontrado em '{fonte}'.")
    return registros


def gerar_csv(saida: Path, fonte: Path = DEFAULT_FONTE, force: bool = False) -> tuple[bool, int]:
    """Gera o arquivo CSV se não existir (ou se force=True). Retorna (gerado, quantidade)."""
    if saida.is_file() and not force:
        return False, 0

    if not fonte.is_file():
        raise FileNotFoundError(
            f"Arquivo de origem '{fonte}' não encontrado para geração automática.\n"
            f"Crie manualmente o arquivo '{saida}' em UTF-8 no formato CSV:\n"
            "  nome,lattes_id\n"
            "  Nome Completo do Pesquisador,1234567890123456"
        )

    registros = extrair_roster_ids(fonte)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["nome", "lattes_id"])
        writer.writerows(registros)
    return True, len(registros)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera Muninn/etl/entradas/lattes.csv a partir do ROSTER_IDS.")
    parser.add_argument("--fonte", type=Path, default=DEFAULT_FONTE, help="Arquivo Python contendo ROSTER_IDS")
    parser.add_argument("--saida", type=Path, default=DEFAULT_SAIDA, help="Caminho de saída do CSV (nome,lattes_id)")
    parser.add_argument("--force", action="store_true", help="Sobrescreve o arquivo de saída mesmo se já existir")
    args = parser.parse_args(argv)

    try:
        gerado, total = gerar_csv(saida=args.saida, fonte=args.fonte, force=args.force)
    except (FileNotFoundError, ValueError, SyntaxError) as exc:
        print(f"❌ Erro ao preparar lista do Lattes:\n{exc}", file=sys.stderr)
        return 1

    if gerado:
        print(f"✓ Lista do Lattes gerada em '{args.saida}' ({total} registros).")
    else:
        print(f"→ Lista do Lattes já existe em '{args.saida}'; mantendo arquivo atual.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
