#!/usr/bin/env python3
"""
Utilitário para inspecionar e consultar o banco de dados acadêmicos SQLite (`dados.db`).

Uso:
  python Adito/scripts/ver_dados.py
      -> Lista todas as tabelas e views e quantidade de registros.

  python Adito/scripts/ver_dados.py <nome_da_tabela_ou_view>
      -> Mostra o esquema e as 5 primeiras linhas da tabela ou view.

  python Adito/scripts/ver_dados.py "SELECT * FROM vfact_extensao_acao_resolved LIMIT 3"
      -> Executa qualquer consulta SQL e imprime os resultados.

  python Adito/scripts/ver_dados.py -i
      -> Abre um shell SQL interativo.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "Adito" / "app" / "data" / "dados.db"


def conectar() -> sqlite3.Connection:
    if not DB_PATH.exists():
        sys.exit(f"Erro: banco não encontrado em {DB_PATH}.\nRode antes: python Adito/scripts/popular_banco.py")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def formatar_tabela(colunas: list[str], linhas: list[Iterable]) -> str:
    if not linhas:
        return " | ".join(colunas) + "\n(0 linhas)"
    linhas_str = [[str(v) if v is not None else "NULL" for v in r] for r in linhas]
    larguras = [len(c) for c in colunas]
    for r in linhas_str:
        for i, val in enumerate(r):
            larguras[i] = max(larguras[i], len(val))
    header = " | ".join(c.ljust(larguras[i]) for i, c in enumerate(colunas))
    divisor = "-+-".join("-" * larguras[i] for i in range(len(colunas)))
    body = "\n".join(" | ".join(val.ljust(larguras[i]) for i, val in enumerate(r)) for r in linhas_str)
    return f"{header}\n{divisor}\n{body}"


def listar_tabelas(conn: sqlite3.Connection):
    print("=" * 80)
    print(f"Banco Acadêmico Relacional (SQLite): {DB_PATH}")
    print("=" * 80)

    print("\n📊 6 VIEWS ANALÍTICAS DINÂMICAS (OLTP):")
    print("-" * 80)
    cursor = conn.execute(
        """
        SELECT name AS view_name
        FROM sqlite_master
        WHERE type = 'view' AND name LIKE 'vfact_%'
        ORDER BY name;
        """
    )
    views = [row[0] for row in cursor.fetchall()]
    view_rows = []
    for v in views:
        qtd = conn.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
        view_rows.append([v, str(qtd)])
    print(formatar_tabela(["View Analítica", "Total Registros"], view_rows))

    print("\n📦 42 TABELAS RELACIONAIS EM 3FN:")
    print("-" * 80)
    cursor = conn.execute(
        """
        SELECT name AS table_name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
        """
    )
    tabelas = [row[0] for row in cursor.fetchall()]
    tab_rows = []
    for t in tabelas:
        qtd = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        tab_rows.append([t, str(qtd)])
    print(formatar_tabela(["Tabela 3FN", "Registros"], tab_rows))
    print(f"\nTotal de tabelas base: {len(tabelas)}")

    print("\n💡 Dica: para ver dados de uma view ou tabela específica, execute:")
    print("   python Adito/scripts/ver_dados.py vfact_extensao_acao_resolved")
    print("   python Adito/scripts/ver_dados.py -i   (para shell interativo)")


def inspecionar_tabela(conn: sqlite3.Connection, nome: str):
    print(f"\n🔍 Inspecionando objeto: {nome}")
    print("-" * 80)

    try:
        cursor = conn.execute(f"PRAGMA table_info({nome});")
        col_rows = cursor.fetchall()
        if not col_rows:
            # Caso de view onde PRAGMA table_info funciona no SQLite moderno
            cursor = conn.execute(f"SELECT * FROM {nome} LIMIT 0;")
            cols = [desc[0] for desc in cursor.description]
            print("COLUNAS:")
            print("\n".join(f"  - {c}" for c in cols))
        else:
            print("COLUNAS:")
            cols_info = [[str(r[1]), str(r[2]), "NOT NULL" if r[3] else "NULLABLE", "PK" if r[5] else ""] for r in col_rows]
            print(formatar_tabela(["Coluna", "Tipo", "Nulidade", "PK"], cols_info))

        print("-" * 80)
        cursor = conn.execute(f"SELECT * FROM {nome} LIMIT 5;")
        amostra = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        print(f"\nAMOSTRA (Primeiras {len(amostra)} linhas):")
        print(formatar_tabela(cols, amostra))
    except Exception as e:
        print(f"Erro ao consultar objeto '{nome}': {e}")


def executar_query(conn: sqlite3.Connection, query: str):
    print(f"\n⚡ Executando consulta SQL:\n{query}")
    print("-" * 80)
    try:
        cursor = conn.execute(query)
        linhas = cursor.fetchall()
        if cursor.description:
            cols = [desc[0] for desc in cursor.description]
            print(formatar_tabela(cols, linhas))
            print(f"\n({len(linhas)} linha(s) retornada(s))")
        else:
            print(f"Consulta executada com sucesso. ({cursor.rowcount} linhas afetadas)")
    except Exception as e:
        print(f"Erro ao executar query: {e}")


def shell_interativo(conn: sqlite3.Connection):
    print("=" * 80)
    print("Shell Interativo SQLite (Somente Leitura) - Adito dados.db")
    print("Digite 'sair' ou pressione Ctrl+C para finalizar.")
    print("=" * 80)

    import readline  # noqa: F401

    while True:
        try:
            cmd = input("\nsqlite> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("sair", "exit", "quit", "\\q"):
                print("Até logo!")
                break
            executar_query(conn, cmd)
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando shell.")
            break


def main():
    conn = conectar()

    if len(sys.argv) == 1:
        listar_tabelas(conn)
    elif sys.argv[1] in ("-i", "--interativo"):
        shell_interativo(conn)
    elif sys.argv[1].strip().upper().startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA")):
        executar_query(conn, " ".join(sys.argv[1:]))
    else:
        inspecionar_tabela(conn, sys.argv[1])

    conn.close()


if __name__ == "__main__":
    main()
