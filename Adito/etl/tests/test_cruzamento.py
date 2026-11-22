import json

import pytest

from adito_etl.comum import gravar_json, ler_json
from adito_etl.cruzamento.cruzar import cruzar, id_opaco, ligar
from adito_etl.cruzamento.leitores import Ocorrencia
from adito_etl.cruzamento.normalizar import (
    forma_invariante, forma_ordenada, nome_implausivel, normalizar_nome)


@pytest.mark.parametrize("entrada, esperado", [
    ("  José  da SILVA ", "jose da silva"),
    ("João D'Ávila", "joao d avila"),
    ("Maria-José Conceição", "maria jose conceicao"),
    ("ANA. B. Souza,", "ana b souza"),
    ("", ""),
    (None, ""),
])
def test_normalizar_nome(entrada, esperado):
    assert normalizar_nome(entrada) == esperado


def test_mesma_forma_vira_uma_pessoa_com_id_estavel():
    pessoas = ligar([
        Ocorrencia("src", "José da Silva", "publico_alvo", "atividade:1"),
        Ocorrencia("src", "JOSE DA SILVA", "publico_alvo", "atividade:2"),  # homônimo sem id: mesma pessoa
        Ocorrencia("sigpesq", "José da  Silva", "orientado", "orientacao:7"),
    ])
    assert len(pessoas) == 1
    p = pessoas[0]
    assert p["id"] == id_opaco("jose silva")
    assert p["nome"] == "José da Silva"
    assert set(p["fontes"]) == {"src", "sigpesq"}
    assert len(p["fontes"]["src"]) == 2


def test_formas_do_horizon():
    assert forma_invariante("Tiago Sérgio dos Exemplo Jr.") == "tiago sergio exemplo junior"
    assert forma_invariante("Tiago Sergio Exemplo Junior") == "tiago sergio exemplo junior"
    assert forma_invariante("João Silva Filho") == "joao silva filho"     # Filho não some
    assert forma_ordenada("SILVA, João") == forma_ordenada("João Silva")


@pytest.mark.parametrize("nome, implausivel", [
    ("Dr", True), ("Prof. Dra", True), ("Maria", True), ("Prof. Maria", True),
    ("", True), ("Maria Souza", False), ("Dr. Maria Souza", False),
])
def test_nome_implausivel(nome, implausivel):
    assert nome_implausivel(nome) is implausivel


def test_liga_sem_particulas_jr_e_ordem_de_forma_transitiva():
    pessoas = ligar([
        Ocorrencia("src", "Tiago Sérgio dos Exemplo Júnior", "equipe_execucao", "atividade:1"),
        Ocorrencia("sigpesq", "Tiago Sergio Exemplo Jr.", "orientador", "orientacao:2"),
        Ocorrencia("lattes", "EXEMPLO JR, Tiago Sergio", "integrante_projeto", "projeto_lattes:x"),
    ])
    assert len(pessoas) == 1
    assert set(pessoas[0]["fontes"]) == {"src", "sigpesq", "lattes"}
    assert len(pessoas[0]["variantes"]) == 3


def test_filho_e_neto_nao_ligam_ao_pai():
    pessoas = ligar([
        Ocorrencia("src", "João Silva", "publico_alvo", "a:1"),
        Ocorrencia("src", "João Silva Filho", "publico_alvo", "a:2"),
        Ocorrencia("src", "João Silva Neto", "publico_alvo", "a:3"),
    ])
    assert len(pessoas) == 3


def test_nome_implausivel_nao_liga():
    pessoas = ligar([
        Ocorrencia("src", "Helder", "publico_alvo", "a:1"),
        Ocorrencia("sigpesq", "Helder", "orientado", "o:1"),
    ])
    assert pessoas == []


def test_nome_exibido_prefere_titular_do_lattes_e_forma_sem_virgula():
    pessoas = ligar([
        Ocorrencia("lattes", "FERRAZ, Márcio Teste", "integrante_projeto", "p:1"),
        Ocorrencia("lattes", "FERRAZ, Márcio Teste", "integrante_projeto", "p:2"),
        Ocorrencia("lattes", "Marcio Teste Ferraz", "integrante_projeto", "p:3"),
    ])
    assert pessoas[0]["nome"] == "Marcio Teste Ferraz"
    pessoas = ligar([
        Ocorrencia("sigpesq", "Márcio Teste Ferraz", "orientador", "o:1"),
        Ocorrencia("lattes", "Marcio Teste Ferraz", "titular_curriculo", "lattes:1", id_fonte="1" * 16),
    ])
    assert pessoas[0]["nome"] == "Marcio Teste Ferraz"


def test_dois_ids_proprios_na_mesma_fonte_viram_ambiguos():
    pessoas = ligar([
        Ocorrencia("lattes", "Ana Souza", "dono_curriculo", "cv:1", id_fonte="1111111111111111"),
        Ocorrencia("lattes", "Ana Souza", "dono_curriculo", "cv:2", id_fonte="2222222222222222"),
        Ocorrencia("src", "Ana Souza", "equipe_execucao", "atividade:3"),
    ])
    assert len(pessoas) == 3
    assert all(p.get("ambiguo") for p in pessoas)
    assert len({p["id"] for p in pessoas}) == 3
    assert all(len(p["fontes"]) == 1 for p in pessoas)  # nada ligado


def _brutos(base):
    gravar_json(base / "brutos" / "src" / "acoes" / "acao_1.json",
                {"acao_id": "1", "Processo nº": "23158.1/2025-01", "Coordenador(a)": "Ana Silva"})
    gravar_json(base / "brutos" / "src" / "participacoes" / "participacoes_23158.1-2025-01.json",
                {"processo": "23158.1/2025-01", "atividades": [{
                    "atividade_id": "55",
                    "publico_alvo": [{"Nome": "Davi Souza"}, {"Nome": "Eva Reis"}],
                    "equipe_execucao": [{"Nome": "Bruno Lima", "Função": "Bolsista"}],
                }]})
    gravar_json(base / "brutos" / "sigpesq" / "projetos" / "relatorio.json",
                {"linhas": [{"Id": 10, "Coordenador": "ANA SILVA",
                             "Pesquisadores": "Bruno Lima; Carla Dias", "Estudantes": None}]})
    gravar_json(base / "brutos" / "sigpesq" / "grupos" / "relatorio.json",
                {"linhas": [{"Sigla": "LEDS", "Lideres": "Ana Silva, Carla Dias"}]})
    (base / "brutos" / "outra").mkdir(parents=True)


def test_cruzar_gera_pessoas_e_relatorio(base):
    _brutos(base)
    rel = cruzar(log=lambda m: None)

    assert rel["fontes_lidas"] == ["sigpesq", "src"]
    assert rel["fontes_sem_leitor"] == ["outra"]
    assert rel["ligadas_por_par"] == {"sigpesq+src": 2}       # Ana Silva, Bruno Lima
    assert rel["sem_par_por_fonte"]["src"] == ["Davi Souza", "Eva Reis"]
    assert rel["sem_par_por_fonte"]["sigpesq"] == ["Carla Dias"]
    assert rel["ambiguos"] == {}

    pessoas = ler_json(base / "trabalho" / "pessoas.json")
    assert {p["nome_normalizado"] for p in pessoas} == {
        "ana silva", "bruno lima", "carla dias", "davi souza", "eva reis"}
    md = (base / "trabalho" / "relatorio_cruzamento.md").read_text(encoding="utf-8")
    assert "| sigpesq+src | 2 |" in md and "outra" in md


def test_cruzar_e_deterministico(base):
    _brutos(base)
    cruzar(log=lambda m: None)
    primeiro = {f.name: f.read_bytes() for f in (base / "trabalho").iterdir()}
    cruzar(log=lambda m: None)
    segundo = {f.name: f.read_bytes() for f in (base / "trabalho").iterdir()}
    assert primeiro == segundo


def test_cruzar_sem_brutos_explica(base):
    with pytest.raises(FileNotFoundError, match="extratores"):
        cruzar(log=lambda m: None)
