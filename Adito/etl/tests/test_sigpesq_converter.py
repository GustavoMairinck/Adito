from datetime import datetime

from openpyxl import Workbook

from adito_etl.comum import ler_json
from adito_etl.fontes.sigpesq.converter import converter, converter_pasta
from adito_etl.comum import Execucao


def _xlsx(path, cabecalho, linhas):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.append(cabecalho)
    for linha in linhas:
        ws.append(linha)
    wb.save(path)


def _pasta_agente(raiz):
    _xlsx(raiz / "research_group" / "Relatorio_1.xlsx",
          ["ParecerDiretoria", "Sigla", "Nome", "Column1", "Site", "AreaConhecimento", "Unidade", "Lideres"],
          [["Certificado", "LEDS", "Lab X", "http://dgp.cnpq.br/dgp/espelhogrupo/1234567890123456",
            None, "Computação", "Serra", "Ana Silva (ana@ifes.edu.br), Bruno Lima (b@ifes.edu.br)"]])
    _xlsx(raiz / "research_projects" / "Relatorio_2.xlsx",
          ["Id", "Titulo", "Coordenador", "EmailCoordenador", "Pesquisadores", "Estudantes", "Inicio"],
          [[10, "Projeto A", "Ana Silva", "ana@ifes.edu.br", "Bruno Lima; Carla Dias", "Davi Souza",
            datetime(2025, 3, 1)]])
    _xlsx(raiz / "advisorships" / "2025" / "Relatorio_3.xlsx",
          ["Id", "Orientador", "OrientadorEmail", "Orientado", "OrientadoCpf", "CelularOrientado",
           "Valor", "ColunaNova"],
          [[7, "Ana Silva", "ana@ifes.edu.br", "Davi Souza", "123.456.789-01", "27999998888", "700,00", "x"]])


def test_converte_filtra_colunas_e_tira_emails(base):
    origem = base / "trabalho" / "xlsx"
    _pasta_agente(origem)
    exe = converter(origem)

    grupos = ler_json(base / "brutos" / "sigpesq" / "grupos" / "relatorio.json")
    assert grupos["linhas"][0]["Lideres"] == "Ana Silva, Bruno Lima"
    assert grupos["linhas"][0]["Column1"].endswith("1234567890123456")

    projetos = ler_json(base / "brutos" / "sigpesq" / "projetos" / "relatorio.json")
    assert "EmailCoordenador" not in projetos["colunas"]
    assert projetos["linhas"][0]["Inicio"] == "2025-03-01T00:00:00"

    orient = ler_json(base / "brutos" / "sigpesq" / "orientacoes" / "2025.json")
    assert set(orient["linhas"][0]) == {"Id", "Orientador", "Orientado", "Valor"}

    assert exe.avisos == ["orientacoes: coluna descartada (fora da lista de permitidas): ColunaNova"]
    assert not exe.falhas
    assert origem.exists()  # `sigpesq-converter` não apaga a origem


def test_apagar_remove_todos_os_xlsx(base):
    origem = base / "trabalho" / "sigpesq_xlsx"
    _pasta_agente(origem)
    converter_pasta(origem, Execucao("sigpesq", "download"), apagar=True)
    assert not origem.exists()
    assert not list(base.rglob("*.xlsx"))


def test_relatorio_ausente_vira_aviso(base):
    origem = base / "vazio"
    origem.mkdir()
    exe = converter(origem)
    assert len(exe.avisos) == 3 and not exe.falhas
