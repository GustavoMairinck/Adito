"""Relatórios do SigPesq e colunas que ficam no bruto (BR01).

Levantadas dos XLSX que o horizon_etl baixou. Ficam fora: e-mails, CPF e
celulares (as colunas `*Email`, `*Cpf`, `Celular*`). Aprovadas pelo usuário em
2026-11-10 (US-ETL-03, CA2).

Observações:
- `grupos.Column1` é a URL do espelho do grupo no DGP/CNPq (usada pelo US-ETL-04).
- `grupos.Lideres` vem como "Nome (email), Nome (email)"; os e-mails entre
  parênteses são removidos por `pii.sanitizar`.
- `orientacoes.Valor` é o valor da bolsa; fica (aprovado em 2026-11-10).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Relatorio:
    pasta: str           # subpasta que a sigpesq-agent cria
    nome: str            # subpasta em brutos/sigpesq/
    permitidas: frozenset[str]


GRUPOS = Relatorio("research_group", "grupos", frozenset({
    "ParecerDiretoria", "Sigla", "Nome", "Column1", "Site", "AreaConhecimento",
    "Unidade", "Lideres",
}))

PROJETOS = Relatorio("research_projects", "projetos", frozenset({
    "CampusExecucao", "Id", "Inicio", "Fim", "Titulo", "Coordenador",
    "Pesquisadores", "Estudantes", "QtdOutros", "GrupoPesquisa",
    "GrupoPesquisaExterno", "LinhaPesquisa", "QtdPts", "QtdFinanciamentos",
    "AreaConhecimento", "PalavraChave", "Natureza", "ParceiroDemandante",
    "ParceriaPoloInovacaoConfirmado", "Sigilo", "ParecerDiretoria",
}))

ORIENTACOES = Relatorio("advisorships", "orientacoes", frozenset({
    "Id", "Ano", "Gerenciamento", "Modalidade", "Programa", "Valor", "Inicio", "Fim",
    "AgFinanciadora", "AceiteOrientador", "AceiteOrientadorData", "AceiteOrientado",
    "AceiteOrientadoData", "Cancelado", "CanceladoPor", "Ciente", "AvaliacaoRelatorio",
    "CampusExecucao", "Orientador", "CampusOrientador", "Orientado", "Curso", "Campus",
    "Edital", "CodPT", "TituloPT", "CodPJ", "TituloPJ", "AreaConhecimento", "GradeArea",
}))

RELATORIOS = (GRUPOS, PROJETOS, ORIENTACOES)
