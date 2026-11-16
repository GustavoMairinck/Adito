#!/usr/bin/env python3
"""Gera o banco analítico DuckDB OLAP (`dados.duckdb`) a partir dos 41 JSONs exportados.

Lê `Adito/etl/saida/json/manifesto.json` e os 41 arquivos `<tabela>.json`,
recria o schema `unificado` com tipagem explícita no DuckDB e materializa as
6 tabelas fato (`CREATE TABLE main.vfact_*_resolved AS SELECT ...`) definidas em
`Docs/Fatos/PropostaFatos.md` em formato colunar nativo para máxima velocidade OLAP.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import duckdb

RAIZ_REPO = Path(__file__).resolve().parents[2]
PASTA_JSON_PADRAO = RAIZ_REPO / "Adito" / "etl" / "saida" / "json"
PROPOSTA_PADRAO = RAIZ_REPO / "Docs" / "Fatos" / "PropostaFatos.md"
SAIDA_DUCKDB_PADRAO = RAIZ_REPO / "Adito" / "app" / "data" / "dados.duckdb"

CONTAGENS_ESPERADAS_FATOS: dict[str, int] = {
    "vfact_extensao_acao_resolved": 207,
    "vfact_extensao_participacao_resolved": 6741,
    "vfact_projeto_pesquisa_resolved": 236,
    "vfact_orientacao_bolsa_resolved": 1203,
    "vfact_producao_cientifica_resolved": 1232,
    "vfact_grupo_pesquisa_membro_resolved": 553,
}

_RE_VIEW_SQL = re.compile(
    r"CREATE\s+OR\s+REPLACE\s+VIEW\s+unificado\.(vfact_[a-z0-9_]+_resolved)\s+AS\s+(SELECT\b.*?);",
    re.IGNORECASE | re.DOTALL,
)


def mapear_tipo_duckdb(tipo_pg: str) -> str:
    """Converte o tipo PostgreSQL do `manifesto.json` para o tipo colunar equivalente no DuckDB."""
    t = tipo_pg.strip().lower()
    if t in ("bigint", "int8"):
        return "BIGINT"
    if t in ("integer", "int", "int4"):
        return "INTEGER"
    if t in ("smallint", "int2"):
        return "SMALLINT"
    if t in ("boolean", "bool"):
        return "BOOLEAN"
    if t == "date":
        return "DATE"
    if t.startswith("numeric(") or t.startswith("decimal("):
        argumentos = t[t.find("(") :]
        return f"DECIMAL{argumentos}"
    if t in ("numeric", "decimal"):
        return "DECIMAL(18,2)"
    if t in ("double precision", "float8", "real", "float4"):
        return "DOUBLE"
    # text, varchar e ENUMs de domínio do PostgreSQL (tipo_*) viram VARCHAR no DuckDB
    return "VARCHAR"


def extrair_fatos_proposta(proposta_path: Path) -> list[tuple[str, str]]:
    """Extrai os pares `(nome_fato, select_sql)` das 6 views em `Docs/Fatos/PropostaFatos.md`."""
    if not proposta_path.exists():
        raise FileNotFoundError(f"Arquivo de proposta não encontrado: {proposta_path}")
    conteudo = proposta_path.read_text(encoding="utf-8")
    encontrados = [
        (match.group(1).lower(), match.group(2).strip())
        for match in _RE_VIEW_SQL.finditer(conteudo)
    ]
    if len(encontrados) != 6:
        nomes = [nome for nome, _ in encontrados]
        raise ValueError(
            f"Esperadas 6 definições vfact_*_resolved em {proposta_path}, "
            f"mas foram encontradas {len(encontrados)}: {nomes}"
        )
    return encontrados


def _criar_tabela_base(
    conn: duckdb.DuckDBPyConnection,
    nome_tabela: str,
    meta_tabela: dict[str, Any],
    registros: list[dict[str, Any]],
    arquivo_json: Path | None = None,
) -> int:
    """Cria `unificado.<nome_tabela>` no DuckDB e carrega os registros do JSON."""
    colunas_meta: list[dict[str, Any]] = meta_tabela.get("colunas", [])
    if not colunas_meta:
        raise ValueError(f"Tabela '{nome_tabela}' sem colunas no manifesto.json.")

    defs_colunas: list[str] = []
    nomes_colunas: list[str] = []
    mapa_colunas_json: list[str] = []
    for col in colunas_meta:
        nome_col = col["nome"]
        tipo_duck = mapear_tipo_duckdb(col["tipo"])
        not_null = "" if col.get("anulavel", True) else " NOT NULL"
        defs_colunas.append(f'"{nome_col}" {tipo_duck}{not_null}')
        nomes_colunas.append(nome_col)
        mapa_colunas_json.append(f"'{nome_col}': '{tipo_duck}'")

    ddl = f'CREATE TABLE unificado."{nome_tabela}" ({", ".join(defs_colunas)})'
    conn.execute(ddl)

    if registros:
        cols_quoted = ", ".join(f'"{c}"' for c in nomes_colunas)
        if arquivo_json is not None and arquivo_json.exists():
            spec_columns = "{" + ", ".join(mapa_colunas_json) + "}"
            conn.execute(
                f'INSERT INTO unificado."{nome_tabela}" ({cols_quoted}) '
                f"SELECT {cols_quoted} FROM read_json(?, format='array', columns={spec_columns})",
                [str(arquivo_json)],
            )
        else:
            placeholders = ", ".join(["?"] * len(nomes_colunas))
            insert_sql = f'INSERT INTO unificado."{nome_tabela}" ({cols_quoted}) VALUES ({placeholders})'
            valores = [
                tuple(linha.get(col_name) for col_name in nomes_colunas)
                for linha in registros
            ]
            conn.executemany(insert_sql, valores)

    total_carregado = conn.execute(f'SELECT COUNT(*) FROM unificado."{nome_tabela}"').fetchone()[0]
    esperado = int(meta_tabela.get("linhas", len(registros)))
    if total_carregado != esperado:
        raise ValueError(
            f"Divergência de contagem na tabela unificado.{nome_tabela}: "
            f"manifesto={esperado}, carregado={total_carregado}"
        )
    return int(total_carregado)


def gerar_banco_duckdb(
    pasta_json: Path = PASTA_JSON_PADRAO,
    proposta_path: Path = PROPOSTA_PADRAO,
    saida_duckdb: Path = SAIDA_DUCKDB_PADRAO,
    contagens_esperadas_fatos: dict[str, int] | None = CONTAGENS_ESPERADAS_FATOS,
) -> dict[str, Any]:
    """Constrói o arquivo `.duckdb` com as 41 tabelas em `unificado` e as 6 tabelas fato em `main`.

    Retorna um dicionário de resumo com contagens das tabelas base e das 6 tabelas fato.
    """
    manifesto_path = pasta_json / "manifesto.json"
    if not manifesto_path.exists():
        raise FileNotFoundError(f"Manifesto não encontrado em {manifesto_path}")

    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    tabelas_meta: dict[str, dict[str, Any]] = manifesto.get("tabelas", {})
    if not tabelas_meta:
        raise ValueError(f"Manifesto em {manifesto_path} não contém 'tabelas'.")

    fatos_sql = extrair_fatos_proposta(proposta_path)

    saida_duckdb = Path(saida_duckdb).resolve()
    saida_duckdb.parent.mkdir(parents=True, exist_ok=True)
    for candidato in (saida_duckdb, Path(f"{saida_duckdb}.wal")):
        if candidato.exists():
            candidato.unlink()

    resumo_tabelas: dict[str, int] = {}
    resumo_fatos: dict[str, int] = {}

    conn = duckdb.connect(str(saida_duckdb), config={"storage_compatibility_version": "v1.2.0"})
    try:
        conn.execute("CREATE SCHEMA IF NOT EXISTS unificado")

        for nome_tabela in sorted(tabelas_meta.keys()):
            arquivo_json = pasta_json / f"{nome_tabela}.json"
            if not arquivo_json.exists():
                raise FileNotFoundError(
                    f"Arquivo JSON da tabela '{nome_tabela}' não encontrado: {arquivo_json}"
                )
            registros = json.loads(arquivo_json.read_text(encoding="utf-8"))
            if not isinstance(registros, list):
                raise ValueError(f"O arquivo {arquivo_json} deve conter uma lista JSON.")
            resumo_tabelas[nome_tabela] = _criar_tabela_base(
                conn, nome_tabela, tabelas_meta[nome_tabela], registros, arquivo_json=arquivo_json
            )

        # Materializa as 6 tabelas fato como TABLE no schema main (máxima velocidade OLAP)
        # e expõe views equivalentes em unificado.<nome_fato> por compatibilidade.
        for nome_fato, select_sql in fatos_sql:
            conn.execute(f'CREATE TABLE main."{nome_fato}" AS {select_sql}')
            conn.execute(
                f'CREATE OR REPLACE VIEW unificado."{nome_fato}" AS '
                f'SELECT * FROM main."{nome_fato}"'
            )
            contagem_fato = conn.execute(
                f'SELECT COUNT(*) FROM main."{nome_fato}"'
            ).fetchone()[0]
            resumo_fatos[nome_fato] = int(contagem_fato)

            if contagens_esperadas_fatos and nome_fato in contagens_esperadas_fatos:
                esperado_fato = contagens_esperadas_fatos[nome_fato]
                if contagem_fato != esperado_fato:
                    raise ValueError(
                        f"Contagem divergente na tabela fato '{nome_fato}': "
                        f"esperado={esperado_fato}, obtido={contagem_fato}"
                    )

        conn.execute("CHECKPOINT")
    finally:
        conn.close()

    return {
        "arquivo_duckdb": str(saida_duckdb),
        "total_tabelas_base": len(resumo_tabelas),
        "total_linhas_base": sum(resumo_tabelas.values()),
        "tabelas_base": resumo_tabelas,
        "fatos_materializados": resumo_fatos,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera o banco analítico DuckDB OLAP (dados.duckdb) com as 6 tabelas fato materializadas."
    )
    parser.add_argument(
        "--pasta-json",
        type=Path,
        default=PASTA_JSON_PADRAO,
        help=f"Pasta contendo manifesto.json e os 41 JSONs (padrão: {PASTA_JSON_PADRAO})",
    )
    parser.add_argument(
        "--proposta",
        type=Path,
        default=PROPOSTA_PADRAO,
        help=f"Caminho para PropostaFatos.md (padrão: {PROPOSTA_PADRAO})",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path(os.environ.get("ORACULO_DADOS_DB") or SAIDA_DUCKDB_PADRAO),
        help=f"Caminho do arquivo .duckdb de saída (padrão: {SAIDA_DUCKDB_PADRAO})",
    )
    parser.add_argument(
        "--sem-validar-contagens-fixas",
        action="store_true",
        help="Não exige as contagens fixas da base de referência para as 6 tabelas fato.",
    )
    args = parser.parse_args(argv)

    esperadas = None if args.sem_validar_contagens_fixas else CONTAGENS_ESPERADAS_FATOS
    resumo = gerar_banco_duckdb(
        pasta_json=args.pasta_json,
        proposta_path=args.proposta,
        saida_duckdb=args.saida,
        contagens_esperadas_fatos=esperadas,
    )

    print(f"Banco DuckDB OLAP gerado com sucesso em: {resumo['arquivo_duckdb']}")
    print(
        f"  Tabelas base em unificado: {resumo['total_tabelas_base']} "
        f"({resumo['total_linhas_base']} linhas totais)"
    )
    print("  Tabelas fato materializadas em main:")
    for nome_fato, qtd in resumo["fatos_materializados"].items():
        print(f"    - {nome_fato}: {qtd} linhas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
