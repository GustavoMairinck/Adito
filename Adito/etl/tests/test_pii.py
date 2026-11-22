import json

import pytest

from adito_etl import pii
from adito_etl.comum import gravar_json


@pytest.mark.parametrize("texto", [
    '{"doc": "123.456.789-01"}',
    '{"doc": "12345678901"}',
    '{"contato": "aluno@example.com"}',
    '{"CPF": "oculto"}',
    '{"OrientadoEmail": null}',
    '{"CelularOrientado": null}',
    '{"Nasc.": "x"}',
])
def test_auditar_bloqueia(texto):
    with pytest.raises(pii.PIIEncontrada):
        pii.auditar(texto)


def test_auditar_aceita_nome_processo_e_ids():
    pii.auditar(json.dumps({
        "Nome": "Fulano de Tal", "Processo nº": "23158.001712/2025-14",
        "lattes_id": "1234567890123456", "Valor": "400,00", "Coordenador(a)": "Ana",
    }))


def test_mascarar_remove_email_entre_parenteses_e_solto():
    texto, n = pii.mascarar("Ana Silva (ana@ifes.edu.br), Bruno Lima (b@x.com)")
    assert texto == "Ana Silva, Bruno Lima"
    assert n == 2
    texto, n = pii.mascarar("contato: c@x.com ou 27999998888, cpf 123.456.789-01")
    assert "@" not in texto and "27999998888" not in texto and "123.456" not in texto
    assert n == 3


def test_sanitizar_percorre_estrutura():
    dados, n = pii.sanitizar({"a": ["x@y.com", {"b": "ok"}], "c": 1})
    assert dados == {"a": ["[e-mail removido]", {"b": "ok"}], "c": 1}
    assert n == 1


def test_gravar_json_recusa_pii_e_nao_cria_arquivo(tmp_path):
    destino = tmp_path / "x.json"
    with pytest.raises(pii.PIIEncontrada):
        gravar_json(destino, {"CPF": "123.456.789-01"})
    assert not destino.exists()


def test_varrer_lista_arquivos_com_pii(tmp_path):
    (tmp_path / "ok.json").write_text('{"Nome": "A"}', encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "ruim.json").write_text('{"x": "a@b.com"}', encoding="utf-8")
    problemas = pii.varrer(tmp_path)
    assert len(problemas) == 1 and "ruim.json" in problemas[0]
