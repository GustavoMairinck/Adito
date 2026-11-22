import sqlite3
import subprocess
import sys
from pathlib import Path
import pytest


def test_popular_banco_sqlite_execution(tmp_path):
    """Valida execução autocontida do popular_banco.py gerando e validando dados.db temporário."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "popular_banco.py"
    etl_dir = repo_root / "etl"
    temp_db = tmp_path / "teste_dados.db"

    if not (etl_dir / "brutos").exists() or not (etl_dir / "trabalho" / "pessoas.json").exists():
        pytest.skip("ainda não há brutos/pessoas.json nesta máquina")

    cmd = [
        sys.executable,
        str(script_path),
        "--etl", str(etl_dir),
        "--banco", str(temp_db)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Falha ao executar popular_banco.py:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

    assert temp_db.exists(), "Arquivo dados.db temporário não foi gerado!"
    assert temp_db.stat().st_size > 1024 * 1024, "Banco dados.db gerado está com tamanho inesperadamente reduzido (< 1 MB)!"

    # Inspeciona banco gerado via sqlite3 read-only
    conn = sqlite3.connect(f"file:{temp_db}?mode=ro", uri=True)

    # 1. Integridade de chaves estrangeiras
    fk_errors = list(conn.execute("PRAGMA foreign_key_check;"))
    assert len(fk_errors) == 0, f"Erros de Foreign Key: {fk_errors}"

    # 2. As 6 views analíticas dinâmicas
    views = [
        "vfact_extensao_acao_resolved",
        "vfact_extensao_participacao_resolved",
        "vfact_grupo_pesquisa_membro_resolved",
        "vfact_orientacao_bolsa_resolved",
        "vfact_producao_cientifica_resolved",
        "vfact_projeto_pesquisa_resolved"
    ]
    for v in views:
        qtd = conn.execute(f"SELECT COUNT(*) FROM {v};").fetchone()[0]
        assert qtd > 0, f"View {v} está vazia!"

    # 3. Validações de sanidade de regras P1 a P12
    # P1: Nenhuma ocorrência de FAPES ou UFES na coluna campus de produção científica
    fapes_ufes = conn.execute(
        "SELECT COUNT(*) FROM vfact_producao_cientifica_resolved WHERE campus IN ('FAPES', 'UFES');"
    ).fetchone()[0]
    assert fapes_ufes == 0, f"P1 violado: {fapes_ufes} registros com campus FAPES/UFES"

    # Flag líder > 0
    lideres = conn.execute("SELECT SUM(flag_lider) FROM vfact_grupo_pesquisa_membro_resolved;").fetchone()[0]
    assert lideres > 0, "Nenhum líder identificado nas lideranças de grupo CNPq"

    # Tempo de participação dias >= 0 ou nulo
    neg_dias = conn.execute(
        "SELECT COUNT(*) FROM vfact_grupo_pesquisa_membro_resolved WHERE tempo_participacao_dias < 0;"
    ).fetchone()[0]
    assert neg_dias == 0, f"P3 violado: {neg_dias} registros com dias negativos"

    # Obra única
    row_prod = conn.execute(
        "SELECT SUM(flag_obra_unica), COUNT(DISTINCT id_producao) FROM vfact_producao_cientifica_resolved;"
    ).fetchone()
    assert row_prod[0] == row_prod[1], f"P4 violado: flag_obra_unica ({row_prod[0]}) != distinct id_producao ({row_prod[1]})"

    conn.close()
