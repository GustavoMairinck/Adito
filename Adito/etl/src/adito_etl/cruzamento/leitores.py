"""Extrai as pessoas de cada fonte a partir de `brutos/<fonte>/`.

Cada ocorrência = (fonte, nome como veio, papel, referência ao registro de
origem, id próprio da fonte quando existir). Leitores: SRC, SigPesq, Lattes e
CNPq/DGP. Só o Lattes tem id próprio de pessoa (o do titular do currículo), que
alimenta a trava de homônimos (BR03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from ..comum import ler_json


@dataclass(frozen=True)
class Ocorrencia:
    fonte: str
    nome: str
    papel: str
    ref: str
    id_fonte: str | None = None


def _nomes(campo: object, separador: str) -> list[str]:
    """Divide uma célula com vários nomes ("A; B; C" ou "A, B")."""
    if not isinstance(campo, str):
        return []
    return [n.strip() for n in re.split(separador, campo) if n.strip()]


# ------------------------------------------------------------------ SRC
def ler_src(pasta: Path) -> Iterator[Ocorrencia]:
    for arq in sorted((pasta / "acoes").glob("acao_*.json")):
        d = ler_json(arq)
        processo = d.get("Processo nº") or d.get("acao_id")
        for nome in _nomes(d.get("Coordenador(a)"), r"[;,]"):
            yield Ocorrencia("src", nome, "coordenador_acao", f"acao:{processo}")
    for arq in sorted((pasta / "participacoes").glob("participacoes_*.json")):
        d = ler_json(arq)
        for ativ in d.get("atividades", []):
            ref = f"atividade:{ativ.get('atividade_id')}"
            for p in ativ.get("publico_alvo", []):
                if p.get("Nome"):
                    yield Ocorrencia("src", p["Nome"], "publico_alvo", ref)
            for p in ativ.get("equipe_execucao", []):
                if p.get("Nome"):
                    yield Ocorrencia("src", p["Nome"], "equipe_execucao", ref)


# ------------------------------------------------------------------ SigPesq
def _linhas(arq: Path) -> list[dict]:
    return ler_json(arq).get("linhas", [])


def ler_sigpesq(pasta: Path) -> Iterator[Ocorrencia]:
    for arq in sorted((pasta / "grupos").glob("*.json")):
        for g in _linhas(arq):
            ref = f"grupo:{g.get('Sigla') or g.get('Nome')}"
            for nome in _nomes(g.get("Lideres"), r","):
                yield Ocorrencia("sigpesq", nome, "lider_grupo", ref)
    for arq in sorted((pasta / "projetos").glob("*.json")):
        for p in _linhas(arq):
            ref = f"projeto:{p.get('Id')}"
            for nome in _nomes(p.get("Coordenador"), r";"):
                yield Ocorrencia("sigpesq", nome, "coordenador_projeto", ref)
            for nome in _nomes(p.get("Pesquisadores"), r";"):
                yield Ocorrencia("sigpesq", nome, "pesquisador_projeto", ref)
            for nome in _nomes(p.get("Estudantes"), r";"):
                yield Ocorrencia("sigpesq", nome, "estudante_projeto", ref)
    for arq in sorted((pasta / "orientacoes").glob("*.json")):
        for o in _linhas(arq):
            ref = f"orientacao:{o.get('Id')}"
            if o.get("Orientador"):
                yield Ocorrencia("sigpesq", o["Orientador"], "orientador", ref)
            if o.get("Orientado"):
                yield Ocorrencia("sigpesq", o["Orientado"], "orientado", ref)


# ------------------------------------------------------------------ Lattes
def ler_lattes(pasta: Path) -> Iterator[Ocorrencia]:
    for arq in sorted(pasta.glob("*.json")):
        if arq.name.startswith("_"):
            continue
        cv = ler_json(arq)
        info = cv.get("informacoes_pessoais") or {}
        ident = str(info.get("id_lattes") or arq.stem)
        if info.get("nome_completo"):
            yield Ocorrencia("lattes", info["nome_completo"], "titular_curriculo",
                             f"lattes:{ident}", id_fonte=ident)
        for secao in ("projetos_pesquisa", "projetos_extensao", "projetos_desenvolvimento"):
            for i, proj in enumerate(cv.get(secao) or []):
                ref = f"projeto_lattes:{ident}:{secao}:{i}"
                for m in proj.get("integrantes") or []:
                    if isinstance(m, dict) and m.get("nome"):
                        papel = "coordenador_projeto" if "coord" in str(m.get("papel", "")).lower() \
                            else "integrante_projeto"
                        yield Ocorrencia("lattes", m["nome"], papel, ref)
        orientacoes = cv.get("orientacoes") or {}
        for situacao in ("em_andamento", "concluidas"):
            por_tipo = orientacoes.get(situacao) or {}
            for tipo in sorted(por_tipo):
                for i, o in enumerate(por_tipo[tipo] or []):
                    if isinstance(o, dict) and o.get("orientando"):
                        yield Ocorrencia("lattes", o["orientando"], "orientado",
                                         f"orientacao_lattes:{ident}:{situacao}:{tipo}:{i}")
        bancas = cv.get("bancas") or {}
        for tipo in sorted(bancas):
            for i, b in enumerate(bancas[tipo] or []):
                if isinstance(b, dict) and b.get("aluno"):
                    yield Ocorrencia("lattes", b["aluno"], "candidato_banca",
                                     f"banca_lattes:{ident}:{tipo}:{i}")


# ------------------------------------------------------------------ CNPq/DGP
# Mesmas chaves de nome que o `CnpqCrawlerAdapter.extract_members` do horizon procura.
_CHAVES_NOME = ("nome", "pesquisadores", "estudantes", "tecnicos", "colaboradores_estrangeiros", "egressos",
                "nome_do_pesquisador", "nome_do_estudante", "nome_do_tecnico", "nome_do_egresso")
_IGNORAR = {"ui-button"}
_PAPEL_RH = {"pesquisadores": "pesquisador_grupo", "estudantes": "estudante_grupo",
             "tecnicos": "tecnico_grupo", "colaboradores_estrangeiros": "colaborador_estrangeiro_grupo"}


def _nome_cnpq(item: dict, tabela: str) -> str | None:
    for chave in (*_CHAVES_NOME, tabela.removeprefix("egressos_"), tabela):
        v = item.get(chave)
        if isinstance(v, str) and v.strip() and v.strip().lower() not in _IGNORAR:
            return v.strip()
    return None


def ler_cnpq(pasta: Path) -> Iterator[Ocorrencia]:
    for arq in sorted(pasta.glob("grupo_*.json")):
        g = ler_json(arq)
        ref = f"grupo_cnpq:{g.get('id_espelho') or arq.stem.removeprefix('grupo_')}"
        for nome in (g.get("identificacao") or {}).get("lideres_do_grupo") or []:
            if isinstance(nome, str) and nome.strip() and nome.strip().lower() not in _IGNORAR:
                yield Ocorrencia("cnpq", nome.strip(), "lider_grupo", ref)
        rh = g.get("recursos_humanos") or g.get("recursos_humanos_do_grupo") or {}
        for tabela in sorted(rh):
            linhas = rh[tabela]
            if not isinstance(linhas, list):
                continue
            papel = "egresso_grupo" if tabela.startswith("egressos") else _PAPEL_RH.get(tabela, "membro_grupo")
            for item in linhas:
                if isinstance(item, dict) and (nome := _nome_cnpq(item, tabela)):
                    yield Ocorrencia("cnpq", nome, papel, ref)


LEITORES: dict[str, Callable[[Path], Iterator[Ocorrencia]]] = {
    "src": ler_src,
    "sigpesq": ler_sigpesq,
    "lattes": ler_lattes,
    "cnpq": ler_cnpq,
}
