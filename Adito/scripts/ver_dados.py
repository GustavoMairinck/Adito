#!/usr/bin/env python3
"""
Utilitário para inspecionar e consultar o banco DuckDB analítico (`dados.duckdb`).

Uso:
  python Adito/scripts/ver_dados.py
      -> Lista todas as tabelas e quantidade de registros (main e unificado).

  python Adito/scripts/ver_dados.py <nome_da_tabela>
      -> Mostra o esquema e as 5 primeiras linhas da tabela.

  python Adito/scripts/ver_dados.py "SELECT * FROM vfact_extensao_acao_resolved LIMIT 3"
      -> Executa qualquer consulta SQL e imprime os resultados.

  python Adito/scripts/ver_dados.py -i
      -> Abre um shell SQL interativo.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "Adito" / "app" / "data" / "dados.duckdb"

try:
    import duckdb
except ImportError:
    sys.exit("Erro: DuckDB não instalado no ambiente. Ative o .venv: source Adito/app/.venv/bin/activate")


def conectar() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        sys.exit(f"Erro: banco não encontrado em {DB_PATH}.\nRode antes: python Adito/scripts/gerar_duckdb.py")
    return duckdb.connect(
        str(DB_PATH),
        read_only=True,
        config={
            "enable_external_access": False,
            "lock_configuration": True,
        },
    )


def listar_tabelas(conn: duckdb.DuckDBPyConnection):
    print("=" * 80)
    print(f"Banco Analítico: {DB_PATH}")
    print("=" * 80)

    print("\n📊 TABELAS FATO MATERIALIZADAS (Schema: main)")
    print("-" * 80)
    df_fatos = conn.execute(
        """
        SELECT 
            table_name AS "Tabela Fato",
            estimated_size AS "Total Registros"
        FROM duckdb_tables()
        WHERE schema_name = 'main'
        ORDER BY table_name;
        """
    ).df()
    print(df_fatos.to_string(index=False))

    print("\n📦 TABELAS BRUTAS DO ETL (Schema: unificado)")
    print("-" * 80)
    df_unificado = conn.execute(
        """
        SELECT 
            table_name AS "Tabela Unificado",
            estimated_size AS "Registros"
        FROM duckdb_tables()
        WHERE schema_name = 'unificado' AND table_name NOT LIKE 'vfact_%'
        ORDER BY table_name;
        """
    ).df()
    print(f"Total de tabelas unificadas: {len(df_unificado)}")
    print(df_unificado.to_string(index=False))
    print("\n💡 Dica: para ver dados de uma tabela específica, execute:")
    print("   python Adito/scripts/ver_dados.py vfact_extensao_acao_resolved")
    print("   python Adito/scripts/ver_dados.py -i   (para shell interativo)")


def inspecionar_tabela(conn: duckdb.DuckDBPyConnection, tabela: str):
    schema = "unificado" if "." in tabela and tabela.startswith("unificado.") else "main"
    nome_limpo = tabela.split(".")[-1]

    print(f"\n🔍 Inspecionando tabela: {schema}.{nome_limpo}")
    print("-" * 80)

    try:
        desc = conn.execute(f'DESCRIBE "{nome_limpo}";').df()
        print("COLUNAS:")
        print(desc[["column_name", "column_type"]].to_string(index=False))
        print("-" * 80)

        amostra = conn.execute(f'SELECT * FROM "{nome_limpo}" LIMIT 5;').df()
        print(f"\nAMOSTRA (Primeiras {len(amostra)} linhas):")
        print(amostra.to_string())
    except Exception as e:
        print(f"Erro ao consultar tabela '{tabela}': {e}")


def executar_sql(conn: duckdb.DuckDBPyConnection, sql: str):
    print(f"\nExecutando SQL:\n{sql}\n")
    print("-" * 80)
    try:
        df = conn.execute(sql).df()
        print(df.to_string())
        print(f"\n({len(df)} linha(s) retornada(s))")
    except Exception as e:
        print(f"Erro no SQL: {e}")


def modo_interativo(conn: duckdb.DuckDBPyConnection):
    print("\n🐚 Shell SQL Interativo do DuckDB (digite 'sair' ou 'exit' para encerrar)")
    print("-" * 80)
    while True:
        try:
            query = input("\nduckdb> ").strip()
            if not query:
                continue
            if query.lower() in ("sair", "exit", "quit", "q"):
                print("Até logo!")
                break
            df = conn.execute(query).df()
            print(df.to_string())
            print(f"({len(df)} linhas)")
        except KeyboardInterrupt:
            print("\nEncerrado.")
            break
        except Exception as e:
            print(f"Erro: {e}")


def main():
    conn = conectar()
    if len(sys.argv) == 1:
        listar_tabelas(conn)
    elif sys.argv[1] in ("-i", "--interativo", "shell"):
        modo_interativo(conn)
    elif sys.argv[1].strip().upper().startswith("SELECT") or sys.argv[1].strip().upper().startswith("WITH"):
        executar_sql(conn, " ".join(sys.argv[1:]))
    else:
        inspecionar_tabela(conn, sys.argv[1])


if __name__ == "__main__":
    main()
