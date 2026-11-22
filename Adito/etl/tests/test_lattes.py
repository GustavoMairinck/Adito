import json

from adito_etl.comum import Execucao, ler_json
from adito_etl.cruzamento.leitores import ler_lattes
from adito_etl.fontes.lattes.converter import converter_pasta, filtrar_curriculo, sem_contato
from adito_etl.fontes.lattes.download import ler_lista

ID = "1234567890123456"


def _cv(nome="Ana Souza"):
    return {
        "informacoes_pessoais": {
            "id_lattes": ID, "nome_completo": nome, "nome_citacoes": "SOUZA, A.",
            "sexo": "Feminino", "endereco_profissional": "Rua X, Telefone: (27) 33489200",
            "texto_resumo": "Contato: ana@ifes.edu.br. Pesquisa em redes.",
            "campo_novo": "x",
        },
        "projetos_pesquisa": [{"nome": "P1", "integrantes": [
            {"nome": "Ana Souza", "papel": "Coordenador"}, {"nome": "Bruno Lima", "papel": "Integrante"}]}],
        "orientacoes": {"concluidas": {"mestrado": [{"titulo": "T", "orientando": "Carla Dias"}]},
                        "em_andamento": {}},
        "bancas": {"mestrado": [{"aluno": "Davi Reis", "titulo_trabalho": "X"}]},
        "secao_nova": {"a": 1},
    }


def test_filtro_tira_sexo_mantem_endereco_sem_telefone_e_tira_secao_nova():
    filtrado, descartados = filtrar_curriculo(_cv())
    info = filtrado["informacoes_pessoais"]
    assert "sexo" not in info and "campo_novo" not in info   # padrão falso do scriptLattes
    assert info["endereco_profissional"] == "Rua X,"
    assert sem_contato("Ifes, Serra, ES Telefone: (27) 33489200 Fax: (27) 33489207 URL da Homepage: http://x") \
        == "Ifes, Serra, ES URL da Homepage: http://x"
    assert "secao_nova" not in filtrado
    assert descartados == {"secao_nova", "informacoes_pessoais.campo_novo"}


def test_converter_mascara_email_e_recusa_curriculo_vazio(base, tmp_path):
    origem = tmp_path / "json"
    origem.mkdir()
    (origem / f"00_Ana-Souza_{ID}.json").write_text(json.dumps(_cv()), encoding="utf-8")
    vazio = _cv("[Nome-nao-identificado]")
    vazio["informacoes_pessoais"]["id_lattes"] = "6543210987654321"
    (origem / "01_x_6543210987654321.json").write_text(json.dumps(vazio), encoding="utf-8")
    exe = Execucao("lattes", "conversao")
    converter_pasta(origem, exe)
    gravado = ler_json(base / "brutos" / "lattes" / f"{ID}.json")
    assert "@" not in json.dumps(gravado)
    assert not (base / "brutos" / "lattes" / "6543210987654321.json").exists()
    assert exe.contagens["curriculos"] == 1 and len(exe.falhas) == 1


def test_leitor_lattes(base, tmp_path):
    origem = tmp_path / "json"
    origem.mkdir()
    (origem / f"00_{ID}.json").write_text(json.dumps(_cv()), encoding="utf-8")
    converter_pasta(origem, Execucao("lattes", "conversao"))
    ocs = list(ler_lattes(base / "brutos" / "lattes"))
    papeis = {(o.nome, o.papel, o.id_fonte) for o in ocs}
    assert ("Ana Souza", "titular_curriculo", ID) in papeis
    assert ("Ana Souza", "coordenador_projeto", None) in papeis
    assert ("Bruno Lima", "integrante_projeto", None) in papeis
    assert ("Carla Dias", "orientado", None) in papeis
    assert ("Davi Reis", "candidato_banca", None) in papeis


def test_ler_lista(tmp_path):
    csv = tmp_path / "lattes.csv"
    csv.write_text("nome,lattes_id\nAna,1234567890123456\nBia,123\nAna,1234567890123456\n,1111111111111111\n",
                   encoding="utf-8")
    validos, invalidos = ler_lista(csv)
    assert validos == [("Ana", "1234567890123456")]
    assert len(invalidos) == 2


def test_agencia_da_orientacao():
    from adito_etl.fontes.lattes.financiadores import agencia
    base = "Ana. Título. 2026. Dissertação (Mestrado em X) - "
    ifes = "Instituto Federal de Educação, Ciência e Tecnologia do Espírito Santo"
    assert agencia(base + ifes + ", Fundação de Amparo à Pesquisa do Espírito Santo. Orientador: Bia.") == \
        "Fundação de Amparo à Pesquisa do Espírito Santo"
    assert agencia(base + ifes + ", . Orientador: Bia.") is None
    assert agencia(base + ifes + ". Orientador: Bia.") is None
    assert agencia(base + "Instituto Federal de Educação, Ciência e Tecnologia do. Orientador: Bia.") is None
    assert agencia(base + "Universidade Federal do Espírito Santo. Orientador: Bia.") is None
    assert agencia(base + ifes + ", Coordenação de Aperfeiçoamento de Pessoal de Nível Superior. Bia.") == \
        "Coordenação de Aperfeiçoamento de Pessoal de Nível Superior"
