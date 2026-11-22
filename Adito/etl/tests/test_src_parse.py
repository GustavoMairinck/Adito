"""Parsers do SRC contra HTML fixo (sem rede). Portado de SRCEtl tests/test_detail.py."""

from adito_etl.comum import filtrar_colunas
from adito_etl.fontes.src.detalhe import parse_detalhe
from adito_etl.fontes.src.models import Acao
from adito_etl.fontes.src.participacoes import COLUNAS_PERMITIDAS, linhas_da_tabela
from adito_etl.fontes.src.vinculadas import parse_vinculadas

HTML = """
<table><tbody>
<tr>
  <td class="ui-panelgrid-cell"><label class="ui-outputlabel">Processo nº</label></td>
  <td class="ui-panelgrid-cell">23158.001712/2025-14</td>
</tr>
<tr>
  <td class="ui-panelgrid-cell"><label class="ui-outputlabel">Natureza</label></td>
  <td class="ui-panelgrid-cell">Extensão</td>
</tr>
<tr>
  <td class="ui-panelgrid-cell"><label class="ui-outputlabel">Título ação</label></td>
  <td class="ui-panelgrid-cell">Projeto X</td>
</tr>
</tbody></table>
"""


def test_parse_detalhe_pares():
    dados = parse_detalhe(HTML)
    assert dados["Processo nº"] == "23158.001712/2025-14"
    assert dados["Natureza"] == "Extensão"
    assert dados["Título ação"] == "Projeto X"


def test_acao_from_labels_aliases():
    acao = Acao.from_labels("5646", parse_detalhe(HTML), campus="Serra")
    assert acao.acao_id == "5646"
    assert acao.campus == "Serra"
    assert acao.processo == "23158.001712/2025-14"
    assert acao.model_dump(by_alias=True)["Título ação"] == "Projeto X"


def test_parse_vinculadas_ignora_nenhum():
    html = """<table><tbody>
      <tr><td>23158.1/2025-01</td><td>Extensão</td><td>Projeto</td><td>Filha A</td></tr>
      <tr><td>Nenhum registro encontrado</td></tr>
    </tbody></table>"""
    assert parse_vinculadas(html) == [
        {"processo": "23158.1/2025-01", "natureza": "Extensão", "tipo": "Projeto", "titulo": "Filha A"}
    ]


def test_participacoes_descartam_cpf_email_e_avisam_coluna_nova():
    headers = ["Nome", "CPF", "E-mail", "Nasc.", "Função", "Coluna Nova", "Operação"]
    rows = [["Fulana de Tal", "123.456.789-01", "f@x.com", "01/01/2000", "Bolsista", "x", ""],
            ["Nenhum registro"]]
    linhas, novas = filtrar_colunas(linhas_da_tabela(headers, rows), COLUNAS_PERMITIDAS)
    assert linhas == [{"Nome": "Fulana de Tal", "Função": "Bolsista"}]
    assert novas == ["Coluna Nova"]  # CPF/E-mail/Nasc. somem sem aviso; Operação nem entra
