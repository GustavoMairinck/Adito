from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "exportar_json.py"


def _carregar_modulo():
    spec = importlib.util.spec_from_file_location("exportar_json", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exportar_json"] = mod
    spec.loader.exec_module(mod)
    return mod


exportar_json = _carregar_modulo()


def test_constante_tem_as_41_tabelas_da_proposta():
    assert len(exportar_json.TABELAS_PERMITIDAS) == 41
    assert "parceiro_demandante_projeto" in exportar_json.TABELAS_PERMITIDAS
    assert "pessoa" in exportar_json.TABELAS_PERMITIDAS
    assert "orientacao" in exportar_json.TABELAS_PERMITIDAS


def test_montar_sql_exportacao_ordena_pela_pk():
    sql = exportar_json.montar_sql_exportacao(
        tabela="pessoa",
        chave_primaria=["id"],
        colunas=["id", "nome"],
    )
    assert sql == "SELECT coalesce(json_agg(t ORDER BY t.id), '[]'::json) FROM unificado.pessoa t;"


def test_montar_sql_exportacao_ordena_por_todas_as_colunas_sem_pk():
    sql = exportar_json.montar_sql_exportacao(
        tabela="acao_campus",
        chave_primaria=[],
        colunas=["id_organizacao", "id_acao"],
    )
    assert (
        sql
        == "SELECT coalesce(json_agg(t ORDER BY t.id_organizacao, t.id_acao), '[]'::json) "
        "FROM unificado.acao_campus t;"
    )


def test_montar_sql_exportacao_recusa_tabela_fora_da_lista():
    with pytest.raises(ValueError, match="constante da proposta"):
        exportar_json.montar_sql_exportacao(
            tabela="banca_examinadora",
            chave_primaria=["id"],
            colunas=["id", "titulo_trabalho"],
        )
    with pytest.raises(ValueError, match="fora da constante"):
        exportar_json.resolver_tabelas("pessoa,tabela_inexistente")


def test_codigo_nao_contem_comandos_sql_de_escrita():
    codigo = SCRIPT_PATH.read_text(encoding="utf-8")
    proibidas = (
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bCREATE\b",
        r"\bALTER\b",
        r"\bDROP\b",
        r"\bTRUNCATE\b",
        r"\bGRANT\b",
        r"\bCOPY\b[^;\n]*\bFROM\b",
    )
    for padrao in proibidas:
        assert re.search(padrao, codigo, flags=re.IGNORECASE) is None, (
            f"Palavra proibida de escrita encontrada pelo padrão {padrao!r}"
        )


def test_recusa_pasta_saida_nao_ignorada_pelo_git(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("ignorado/\n", encoding="utf-8")

    pasta_nao_ignorada = tmp_path / "exposta" / "json"
    with pytest.raises(exportar_json.ErroExportacao, match="não está ignorada pelo git"):
        exportar_json.verificar_pasta_ignorada_git(pasta_nao_ignorada)

    pasta_ignorada = tmp_path / "ignorado" / "json"
    exportar_json.verificar_pasta_ignorada_git(pasta_ignorada)


@pytest.mark.parametrize(
    ("valor_proibido", "esperado"),
    [
        ("123.456.789-00", "CPF"),
        ("12345678900", "CPF"),
        ("maria.exemplo@example.org", "e-mail"),
    ],
)
def test_deteccao_cpf_e_email_apaga_arquivos_sem_vazar_valor(tmp_path, valor_proibido, esperado):
    arq = tmp_path / "pessoa.json"
    arq.write_text(
        json.dumps([{"id": 1, "nome": f"Maria Exemplo {valor_proibido}"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "manifesto.json").write_text("{}", encoding="utf-8")

    with pytest.raises(exportar_json.ErroExportacao) as exc_info:
        exportar_json.verificar_pii_arquivos(tmp_path, ["pessoa"])

    msg = str(exc_info.value)
    assert "tabela=pessoa" in msg
    assert "coluna=nome" in msg
    assert esperado in msg
    assert valor_proibido not in msg
    assert not arq.exists()
    assert not (tmp_path / "manifesto.json").exists()


def test_pii_aceita_nomes_e_ids_sinteticos_de_16_digitos(tmp_path):
    (tmp_path / "pessoa_lattes.json").write_text(
        json.dumps(
            [{"id": 1, "id_lattes": "1234567890123456", "nome_citacoes": "EXEMPLO, Maria"}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    achados = exportar_json.verificar_pii_arquivos(tmp_path, ["pessoa_lattes"])
    assert achados == []


def _criar_exportacao_sintetica(pasta: Path) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    pessoas = [
        {"id": 1, "nome": "Maria Exemplo"},
        {"id": 2, "nome": "João Exemplo"},
    ]
    pesquisadores = [
        {"id": 1, "id_titulacao": 10, "id_organizacao": 100},
    ]
    manifesto = {
        "gerado_em": "2026-11-12T18:00:00+00:00",
        "commit": "0000000",
        "proposta": {"arquivo": "Docs/Fatos/PropostaFatos.md", "commit": "c91761a"},
        "postgres": "15.17",
        "schema": "unificado",
        "tabelas": {
            "pessoa": {
                "linhas": 2,
                "colunas": [
                    {"nome": "id", "tipo": "bigint", "anulavel": False},
                    {"nome": "nome", "tipo": "text", "anulavel": False},
                ],
                "chave_primaria": ["id"],
                "chaves_estrangeiras": [],
            },
            "pesquisador": {
                "linhas": 1,
                "colunas": [
                    {"nome": "id", "tipo": "bigint", "anulavel": False},
                    {"nome": "id_titulacao", "tipo": "bigint", "anulavel": True},
                    {"nome": "id_organizacao", "tipo": "bigint", "anulavel": True},
                ],
                "chave_primaria": ["id"],
                "chaves_estrangeiras": [
                    {
                        "coluna": "id",
                        "tabela_destino": "pessoa",
                        "coluna_destino": "id",
                        "destino_exportado": True,
                    },
                    {
                        "coluna": "id_organizacao",
                        "tabela_destino": "organizacao",
                        "coluna_destino": "id",
                        "destino_exportado": False,
                    },
                ],
            },
        },
    }
    (pasta / "pessoa.json").write_text(json.dumps(pessoas, ensure_ascii=False), encoding="utf-8")
    (pasta / "pesquisador.json").write_text(
        json.dumps(pesquisadores, ensure_ascii=False), encoding="utf-8"
    )
    (pasta / "manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifesto


def test_so_validar_aceita_exportacao_coerente(tmp_path):
    _criar_exportacao_sintetica(tmp_path)
    rc = exportar_json.main(["--so-validar", str(tmp_path)])
    assert rc == 0


def test_so_validar_recusa_contagem_errada(tmp_path):
    _criar_exportacao_sintetica(tmp_path)
    (tmp_path / "pessoa.json").write_text(
        json.dumps([{"id": 1, "nome": "Maria Exemplo"}], ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(exportar_json.ErroExportacao, match="Contagem divergente"):
        exportar_json.validar_exportacao(tmp_path)
    assert exportar_json.main(["--so-validar", str(tmp_path)]) != 0


def test_so_validar_recusa_coluna_faltando_ou_fora_de_ordem(tmp_path):
    _criar_exportacao_sintetica(tmp_path)
    # Coluna faltando
    (tmp_path / "pessoa.json").write_text(
        json.dumps([{"id": 1}, {"id": 2}], ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(exportar_json.ErroExportacao, match="Colunas divergentes"):
        exportar_json.validar_exportacao(tmp_path)

    # Colunas fora de ordem
    (tmp_path / "pessoa.json").write_text(
        json.dumps(
            [{"nome": "Maria Exemplo", "id": 1}, {"nome": "João Exemplo", "id": 2}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(exportar_json.ErroExportacao, match="Colunas divergentes"):
        exportar_json.validar_exportacao(tmp_path)


def test_so_validar_recusa_fk_quebrada(tmp_path):
    _criar_exportacao_sintetica(tmp_path)
    (tmp_path / "pesquisador.json").write_text(
        json.dumps([{"id": 999, "id_titulacao": 10, "id_organizacao": 100}], ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(exportar_json.ErroExportacao, match="FK quebrada"):
        exportar_json.validar_exportacao(tmp_path)
    assert exportar_json.main(["--so-validar", str(tmp_path)]) != 0
