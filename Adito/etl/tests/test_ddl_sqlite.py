import sqlite3
from pathlib import Path
import pytest


def test_ddl_sqlite_execution_and_integrity():
    """Valida a integridade do DDL 100% SQLite e compilação das 6 Views de Fatos."""
    # Localiza o diretório de scripts SQL relativo à raiz do repositório
    root_dir = Path(__file__).resolve().parents[2]
    sql_dir = root_dir / "scripts" / "sql"
    assert sql_dir.is_dir(), f"Diretório {sql_dir} não encontrado!"

    files = [
        "00_schema.sql",
        "01_tipos_e_dominios.sql",
        "02_tabelas.sql",
        "03_relacionamentos_e_juncoes.sql",
        "04_fatos_views.sql"
    ]

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")

    for fname in files:
        fpath = sql_dir / fname
        assert fpath.exists(), f"Arquivo SQL {fname} ausente!"
        sql_text = fpath.read_text(encoding="utf-8")
        conn.executescript(sql_text)

    # 1. Verifica integridade de chaves estrangeiras
    fk_errors = list(conn.execute("PRAGMA foreign_key_check;"))
    assert len(fk_errors) == 0, f"Erros de Foreign Key encontrados: {fk_errors}"

    # 2. Verifica as 6 views analíticas criadas
    views = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;")]
    expected_views = [
        "vfact_extensao_acao_resolved",
        "vfact_extensao_participacao_resolved",
        "vfact_grupo_pesquisa_membro_resolved",
        "vfact_orientacao_bolsa_resolved",
        "vfact_producao_cientifica_resolved",
        "vfact_projeto_pesquisa_resolved"
    ]
    for ev in expected_views:
        assert ev in views, f"View {ev} não encontrada no schema!"
        # Testa compilação da query da view
        cursor = conn.execute(f"SELECT * FROM {ev} LIMIT 0;")
        col_names = [desc[0] for desc in cursor.description]
        assert len(col_names) > 0, f"View {ev} não possui colunas retornadas"

    conn.close()
