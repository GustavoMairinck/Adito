import pytest

from adito_etl.comum import gravar_json
from adito_etl.cruzamento.leitores import ler_cnpq
from adito_etl.fontes.cnpq.grupos import (
    SemBrutoSigPesq, filtrar_grupo, grupos_do_sigpesq, id_do_espelho)

ID = "1234123412341234"


@pytest.mark.parametrize("url, esperado", [
    (f"http://dgp.cnpq.br/dgp/espelhogrupo/{ID}", ID),
    (f"http://dgp.cnpq.br//dgp/espelhogrupo/{ID}", ID),          # barra dupla
    (f"https://dgp.cnpq.br/dgp/espelhogrupo/{ID} ", ID),
    ("http://dgp.cnpq.br/dgp/espelhogrupo/", None),               # sem id
    ("http://dgp.cnpq.br/dgp/espelhogrupo/123", None),
    (None, None), ("", None),
])
def test_id_do_espelho(url, esperado):
    assert id_do_espelho(url) == esperado


def test_grupos_do_sigpesq(base):
    gravar_json(base / "brutos" / "sigpesq" / "grupos" / "relatorio.json", {"linhas": [
        {"Nome": "LEDS", "Unidade": "Serra", "Column1": f"http://dgp.cnpq.br/dgp/espelhogrupo/{ID}"},
        {"Nome": "Outro", "Unidade": "Vitória", "Column1": "http://dgp.cnpq.br/dgp/espelhogrupo/9999999999999999"},
        {"Nome": "Sem URL", "Unidade": "Serra", "Column1": None},
    ]})
    validos, invalidos = grupos_do_sigpesq("serra")
    assert [g["id"] for g in validos] == [ID]
    assert [g["nome"] for g in invalidos] == ["Sem URL"]
    assert len(grupos_do_sigpesq()[0]) == 2


def test_sem_bruto_do_sigpesq_explica(base):
    with pytest.raises(SemBrutoSigPesq, match="sigpesq"):
        grupos_do_sigpesq()


def test_filtro_tira_endereco_e_chave_pessoal():
    filtrado, descartadas = filtrar_grupo({
        "nome_grupo": "LEDS",
        "identificacao": {"lideres_do_grupo": ["Ana Souza"], "email": "x@y.com"},
        "endereco_contato": {"telefone": "2733489200", "fax": "()", "contato_do_grupo": "a@b.com",
                             "logradouro": "Rodovia ES-010", "cep": "29173087", "website": "http://x",
                             "latitude": "-20.1976045299999"},
        "secao_nova": {},
    })
    assert set(filtrado) == {"nome_grupo", "identificacao", "endereco_contato"}
    assert filtrado["endereco_contato"] == {"logradouro": "Rodovia ES-010", "cep": "29173087",
                                           "website": "http://x", "latitude": "-20.197605"}
    assert "email" not in filtrado["identificacao"]
    assert descartadas == {"secao_nova"}


def test_leitor_cnpq(base):
    gravar_json(base / "brutos" / "cnpq" / f"grupo_{ID}.json", {
        "id_espelho": ID,
        "identificacao": {"lideres_do_grupo": ["Ana Souza", "ui-button"]},
        "recursos_humanos": {
            "pesquisadores": [{"pesquisadores": "Bruno Lima", "titulacao_maxima": "Doutorado"}],
            "estudantes": [{"estudantes": "Carla Dias", "nivel_de_treinamento": "Graduação"}],
            "egressos_pesquisadores": [{"nome": "Davi Reis", "data_fim": "2020"}],
            "egressos_colaboradores_estrangeiros": [{"colaboradores_estrangeiros": "Eva Cunha", "pais": "PT"}],
        },
    })
    ocs = {(o.nome, o.papel, o.ref) for o in ler_cnpq(base / "brutos" / "cnpq")}
    ref = f"grupo_cnpq:{ID}"
    assert ocs == {("Ana Souza", "lider_grupo", ref), ("Bruno Lima", "pesquisador_grupo", ref),
                   ("Carla Dias", "estudante_grupo", ref), ("Davi Reis", "egresso_grupo", ref),
                   ("Eva Cunha", "egresso_grupo", ref)}
