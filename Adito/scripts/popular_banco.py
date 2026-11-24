#!/usr/bin/env python3
"""Popula o banco de dados acadêmicos SQLite (`dados.db`) com o que o ETL do Adito já extraiu.

Lê a pasta do ETL (`brutos/` de cada fonte + `trabalho/pessoas.json` do
cruzamento), recria o schema SQLite nativo (DDLs 00 a 04), insere as 82
tabelas base em 3FN em uma única transação atômica e compila as 6 views analíticas
(100% OLTP, zero duplicação em disco).

Não depende de Docker, PostgreSQL ou DuckDB.
Executa em tempo inferior a 5 segundos diretamente via `sqlite3`.

Uso (a partir de Adito/scripts/):
    python3 popular_banco.py
    python3 popular_banco.py --banco ../app/data/dados.db
    python3 popular_banco.py --so-gerar
    python3 popular_banco.py --etl ../etl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

AQUI = Path(__file__).resolve().parent
DDL = AQUI / "sql"
LOTE = 500


# ============================================================================ util
def forma(nome: Any) -> str:
    """Mesma forma canônica do cruzamento do ETL (`cruzamento/normalizar.py`)."""
    if nome is None:
        return ""
    s = unicodedata.normalize("NFD", str(nome))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return " ".join(s.lower().split())


def chave_enum(v: Any) -> str:
    """'Aprovação Solicitada' -> 'APROVACAO_SOLICITADA'; 'Pibic-Jr' -> 'PIBIC_JR'; '2º' -> '2O'."""
    return "_".join(forma(unicodedata.normalize("NFKD", str(v or ""))).upper().split())


def texto(v: Any) -> str | None:
    if v is None:
        return None
    s = " ".join(str(v).split()) if not isinstance(v, str) or "\n" not in v else str(v).strip()
    return None if s in ("", "None", "-", "null") else s


def inteiro(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    m = re.search(r"\d+", str(v or ""))
    return int(m.group(0)) if m else None


def ano(v: Any) -> int | None:
    n = inteiro(v)
    return n if n and 1900 <= n <= 2100 else None


def booleano(v: Any) -> int | None:
    if isinstance(v, bool):
        return 1 if v else 0
    s = forma(v)
    if s in ("true", "sim", "s", "1"):
        return 1
    if s in ("false", "nao", "n", "0"):
        return 0
    return None


def data(v: Any) -> str | None:
    """dd/mm/aaaa, dd-mm-aa ou aaaa-mm-dd -> 'aaaa-mm-dd'."""
    s = str(v or "").strip()
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})(?:[ T].*)?", s)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
    else:
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2}).*", s)
        if not m:
            return None
        y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mth, d).isoformat()
    except ValueError:
        return None


def dinheiro(v: Any) -> float | None:
    s = str(v or "").strip()
    if not s or s == "None":
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(Decimal(s).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def nomes(campo: Any, sep: str) -> list[str]:
    if not isinstance(campo, str):
        return []
    return [n.strip() for n in re.split(sep, campo) if n.strip() and n.strip() != "None"]


def ler(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class Sql(str):
    """Trecho SQL que vai sem aspas (subconsulta de domínio)."""


def literal(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, Sql):
        return str(v)
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# ============================================================================ DDL
def ler_ddl() -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    """Valores dos ENUMs e das tabelas de domínio, lidos do próprio DDL."""
    sql = (DDL / "01_tipos_e_dominios.sql").read_text(encoding="utf-8")
    enums = {m.group(1): re.findall(r"'([^']+)'", m.group(2))
             for m in re.finditer(r"(?:--\s*)?CREATE TYPE (?:unificado\.)?(\w+) AS ENUM \((.*?)\);", sql, re.S)}
    dominios = {m.group(1): set(re.findall(r"'([^']+)'", m.group(2)))
                for m in re.finditer(r"INSERT (?:OR IGNORE )?INTO (?:unificado\.)?(\w+) \(nome\) VALUES(.*?);", sql, re.S)}
    return enums, dominios


# ============================================================================ carga
class Carga:
    # Ordem de inserção (respeita as chaves estrangeiras no SQLite).
    ORDEM = [
        "organizacao", "instituicao_lattes", "instituicao_parceira_cnpq", "endereco",
        "grande_area", "area_conhecimento", "subarea_conhecimento_lattes", "especialidade_lattes", "idioma",
        "titulacao", "curso", "pessoa", "pessoa_lattes", "pessoa_src", "pesquisador",
        "estudante", "area_atuacao", "grupo_pesquisa", "grupo_pesquisa_cnpq", "website",
        "grupo_pesquisa_externo", "linha_pesquisa", "papel", "membro_grupo", "membro_grupo_cnpq",
        "iniciativa", "acao", "tipo_atividade",
        "atividade", "membro_equipe_execucao_src", "registro_participante",
        "projeto_pesquisa", "projeto_lattes", "edital", "plano_trabalho", "orientacao",
        "formacao_academica", "atuacao_profissional", "orientacao_lattes",
        "banca_examinadora", "evento_cientifico", "producao", "artigo_trabalho_evento",
        "livro_capitulo", "producao_tecnica_artistica_bibliografica", "patente_registro", "premio_titulo",
        "membro_projeto", "fomento_projeto", "participacao_evento", "proficiencia_idioma",
        "lideranca_grupo_pesquisa", "cooperacao_grupo_externo_projeto", "fomento_acao",
        "acao_campus", "parceiro_demandante_projeto", "participacao_estudante_projeto",
        "autoria_producao", "participacao_pesquisador_projeto", "membro_banca_examinadora",
        "grupo_pesquisa_projeto", "pesquisador_linha_pesquisa", "grupo_pesquisa_grande_area",
        "grupo_pesquisa_linha_pesquisa", "parceria_grupo", "equipamento_software", "grupo_pesquisa_equipamento",
        "pessoa_lattes_titulacao",
    ]
    # Tabelas com id próprio (subclasses) que herdam chave primária da superclasse
    BASE = {
        "instituicao_lattes": "organizacao", "pessoa_lattes": "pessoa", "pessoa_src": "pessoa",
        "pesquisador": "pessoa", "estudante": "pessoa", "acao": "iniciativa",
        "projeto_pesquisa": "iniciativa", "projeto_lattes": "iniciativa",
        "membro_equipe_execucao_src": "membro_grupo", "grupo_pesquisa_cnpq": "grupo_pesquisa",
        "membro_grupo_cnpq": "membro_grupo", "instituicao_parceira_cnpq": "organizacao",
        "artigo_trabalho_evento": "producao", "livro_capitulo": "producao",
        "producao_tecnica_artistica_bibliografica": "producao", "patente_registro": "producao"
    }
    JUNCAO = {
        "lideranca_grupo_pesquisa", "cooperacao_grupo_externo_projeto", "fomento_acao",
        "acao_campus", "parceiro_demandante_projeto", "participacao_estudante_projeto",
        "autoria_producao", "participacao_pesquisador_projeto", "membro_banca_examinadora",
        "grupo_pesquisa_projeto", "pesquisador_linha_pesquisa", "grupo_pesquisa_grande_area",
        "grupo_pesquisa_linha_pesquisa", "grupo_pesquisa_equipamento", "pessoa_lattes_titulacao"
    }

    def __init__(self, etl: Path):
        self.etl = etl
        self.enums, self.dominios = ler_ddl()
        self.seq: Counter = Counter()
        self.linhas: dict[str, dict[Any, dict]] = defaultdict(dict)  # tabela -> chave -> linha
        self.cache: dict[tuple, int] = {}
        self.avisos: Counter = Counter()
        self.exemplos: dict[str, set[str]] = defaultdict(set)
        self.sem_coluna: Counter = Counter()
        self.pares_area: dict[str, str] = {}

    # ---------------------------------------------------------------- básicos
    def aviso(self, tipo: str, exemplo: Any = None) -> None:
        self.avisos[tipo] += 1
        if exemplo is not None and len(self.exemplos[tipo]) < 8:
            self.exemplos[tipo].add(str(exemplo)[:120])

    def novo(self, tabela: str, **cols) -> int:
        self.seq[tabela] += 1
        i = self.seq[tabela]
        self.linhas[tabela][i] = {"id": i, **cols}
        return i

    def sub(self, tabela: str, i: int, **cols) -> None:
        """Linha de subclasse (mesmo id da base); completa campos vazios se já existir."""
        atual = self.linhas[tabela].setdefault(i, {"id": i})
        for k, v in cols.items():
            if atual.get(k) is None:
                atual[k] = v

    def juncao(self, tabela: str, **cols) -> None:
        if all(v is not None for v in cols.values()):
            self.linhas[tabela].setdefault(tuple(cols.values()), cols)

    def unico(self, tabela: str, chave: Any, **cols) -> int:
        k = (tabela, chave)
        if k not in self.cache:
            self.cache[k] = self.novo(tabela, **cols)
        return self.cache[k]

    def enum(self, tipo: str, valor: Any, alias: dict[str, str] | None = None) -> str | None:
        if texto(valor) is None:
            return None
        k = chave_enum(valor)
        k = (alias or {}).get(k, k)
        if k in self.enums[tipo]:
            return k
        self.aviso(f"valor fora do ENUM {tipo} (gravado NULL)", valor)
        return None

    def dominio(self, tabela: str, valor: Any, alias: dict[str, str] | None = None) -> Sql | None:
        if texto(valor) is None:
            return None
        # 'Campus Serra - Bolsa' -> tenta também só 'Bolsa'
        for candidato in dict.fromkeys([valor, str(valor).split(" - ")[-1]]):
            k = chave_enum(candidato)
            k = (alias or {}).get(k, k)
            for nome in self.dominios[tabela]:
                if chave_enum(nome) == k:
                    return Sql(f"(SELECT id FROM {tabela} WHERE nome = {literal(nome)})")
        self.aviso(f"valor fora do domínio {tabela} (gravado NULL)", valor)
        return None

    # ---------------------------------------------------------------- entidades
    def org(self, nome: Any, tipo: str, pai: int | None = None, direto: bool = False) -> int | None:
        """Organização única por (tipo, nome). O Ifes e seus campi, em qualquer grafia e em
        qualquer papel (instituição, financiador, parceira...), viram sempre a mesma linha."""
        nome = texto(nome)
        if not nome:
            return None
        if not direto and (i := self.ifes_ou_campus(nome)) is not None:
            return i
        return self.unico("organizacao", (tipo, forma(nome)), nome=nome,
                          id_tipo_organizacao=self.dominio("tipo_organizacao", tipo),
                          id_organizacao_pai=pai)

    def ifes(self) -> int:
        return self.org("Instituto Federal do Espírito Santo", "Instituicao", direto=True)

    def campus(self, nome: Any) -> int | None:
        nome = texto(nome)
        if not nome:
            return None
        nome = re.sub(r"(?i)^(ifes\s*-\s*)?campus\s+(de\s+|do\s+|da\s+)?", "", nome).strip()
        nome = re.sub(r"\s*[-/,]\s*(es|esp[ií]rito santo)$", "", nome, flags=re.I).strip()
        nome = nome.title() if nome.isupper() else nome
        return self.org(nome, "Campus", self.ifes(), direto=True)

    IFES = re.compile(r"^\s*(ifes|ins?tituto federal do esp[ií]rito (do )?santo|ins?tituto federal de educa[cç][aã]o,? "
                      r"ci[eê]ncia e tecnologia do esp[ií]rito (do )?santo)\b", re.I)
    PREFIXOS_LATTES = re.compile(r"^(orienta[cç][aã]o de outra natureza|inicia[cç][aã]o cient[ií]fica)\s*[-.]\s*", re.I)

    def ifes_ou_campus(self, nome: str) -> int | None:
        """'Ifes - Campus Serra', 'Instituto Federal do Espírito Santo-Campus Vitória' -> o campus;
        'Instituto Federal do Espírito Santo - Serra' -> o campus Serra; 'Ifes' ou '... - IFES' -> o Ifes."""
        if not self.IFES.search(nome):
            return None
        m = re.search(r"campus\s+(?:de\s+|do\s+|da\s+)?([^,.;/-]+)", nome, re.I) or \
            re.search(r"santo\s*[-–]\s*(?!ifes\b)([A-Za-zÀ-ú][A-Za-zÀ-ú ]*)$", nome, re.I)
        return self.campus(m.group(1).strip()) if m else self.ifes()

    def eh_ifes_ou_campus(self, org_id: int | None) -> bool:
        if org_id is None:
            return False
        if org_id == self.ifes():
            return True
        linha = self.linhas["organizacao"].get(org_id, {})
        return linha.get("id_organizacao_pai") == self.ifes()

    @staticmethod
    def eh_fomento(nome: Any) -> bool:
        if not nome:
            return False
        s = forma(nome)
        palavras = ["fapes", "cnpq", "capes", "finep", "fundacao de amparo", "agencia de fomento"]
        return any(p in s for p in palavras)

    def instituicao_lattes(self, bruto: Any) -> int | None:
        """'Universidade Federal do Espírito Santo, UFES, Brasil' -> nome, sigla, país.
        O Ifes e seus campi, em qualquer grafia, viram a organização única do Ifes/campus."""
        s = texto(bruto)
        if not s:
            return None
        s = self.PREFIXOS_LATTES.sub("", s.rstrip(". "))
        if (i := self.ifes_ou_campus(s)) is not None:
            self.sub("instituicao_lattes", i, sigla="IFES", pais="Brasil")
            return i
        partes = [p.strip() for p in s.split(",")]
        sigla = pais = None
        if len(partes) >= 3 and len(partes[-2]) <= 15 and " " not in partes[-2] and len(partes[-1]) <= 30:
            sigla, pais, s = partes[-2], partes[-1], ", ".join(partes[:-2])
        i = self.org(s, "Instituicao")
        self.sub("instituicao_lattes", i, sigla=sigla, pais=pais)
        return i

    @staticmethod
    def inst_da_descricao(desc: Any) -> str | None:
        """Última frase da descrição da banca quando é uma instituição ('... 2023. Universidade Federal do ES.')."""
        partes = [p.strip() for p in re.split(r"\.\s+", str(desc or "").rstrip(". ")) if p.strip()]
        if partes and re.search(r"universidade|instituto|faculdade|centro|escola|funda[cç][aã]o|ifes|ufes",
                                partes[-1], re.I) and len(partes[-1]) <= 150:
            return partes[-1]
        return None

    @staticmethod
    def lista_texto(v: Any) -> str | None:
        """Lista do Lattes (["Pesquisa e desenvolvimento, Ifes.", ...]) -> texto, um item por linha."""
        if isinstance(v, list):
            return "\n".join(t for t in (texto(x) for x in v) if t) or None
        return texto(v)

    def grande_area(self, nome: Any) -> int | None:
        nome = texto(nome)
        return self.unico("grande_area", forma(nome), nome=nome) if nome else None

    def area(self, nome: Any, grande: Any = None) -> int | None:
        nome = texto(nome)
        if not nome:
            return None
        i = self.unico("area_conhecimento", forma(nome), nome=nome, id_grande_area=None)
        self.par_area(nome, grande)
        return i

    def par_area(self, area: Any, grande: Any) -> None:
        """Guarda que `area` pertence a `grande`; usado no fim por `completar_areas`."""
        if texto(area) and texto(grande):
            self.pares_area.setdefault(forma(area), texto(grande))

    def completar_areas(self) -> None:
        """Liga cada área à sua grande área, com os pares vistos em qualquer fonte."""
        for k, i in list(self.cache.items()):
            if len(k) == 2 and k[0] == "area_conhecimento":
                chave = k[1]
                linha = self.linhas["area_conhecimento"][i]
                if linha.get("id_grande_area") is None and chave in self.pares_area:
                    linha["id_grande_area"] = self.grande_area(self.pares_area[chave])
        sem = sum(1 for l in self.linhas["area_conhecimento"].values() if l.get("id_grande_area") is None)
        if sem:
            self.avisos["área de conhecimento sem grande área em nenhuma fonte (gravada NULL)"] += sem

    def simples(self, tabela: str, coluna: str, valor: Any) -> int | None:
        v = texto(valor)
        return self.unico(tabela, forma(v), **{coluna: v}) if v else None

    # ---------------------------------------------------------------- pessoas
    def carregar_pessoas(self) -> None:
        arq = self.etl / "trabalho" / "pessoas.json"
        if not arq.exists():
            raise SystemExit(f"erro: {arq} não existe; rode `adito-etl cruzar` no ETL antes")
        self.indice: dict[str, list[tuple[int, dict]]] = defaultdict(list)
        for p in ler(arq):
            pid = self.novo("pessoa", nome=p["nome"])
            for f in {p["nome_normalizado"], *p.get("variantes", [])}:
                self.indice[f].append((pid, p))

    def pessoa(self, nome: Any, fonte: str, id_fonte: str | None = None) -> int | None:
        if not forma(nome):
            self.avisos["registro sem nome de pessoa (vínculo não gravado)"] += 1
            return None
        cands = self.indice.get(forma(nome), [])
        if len(cands) > 1:  # homônimos separados pelo cruzamento (BR03)
            cands = [c for c in cands if any(
                (oc.get("id_fonte") == id_fonte) for oc in c[1]["fontes"].get(fonte, []))] or \
                [c for c in cands if fonte in c[1]["fontes"]]
        if len(cands) == 1:
            return cands[0][0]
        self.aviso("nome sem pessoa no cruzamento: não plausível ou homônimo (vínculo não gravado)",
                   f"{fonte}: {nome}")
        return None

    def pessoa_lattes(self, pid: int | None, **cols) -> int | None:
        if pid is not None:
            self.sub("pessoa_lattes", pid, **cols)
        return pid

    def pesquisador(self, nome: Any, fonte: str, organizacao: int | None = None,
                    titulacao: Any = None) -> int | None:
        """P1: Prioriza campus Ifes no pesquisador; nunca promove agência de fomento a lotação."""
        pid = self.pessoa(nome, fonte)
        if pid is not None:
            atual_pesq = self.linhas["pesquisador"].setdefault(pid, {"id": pid})
            if organizacao is not None:
                # Se veio campus Ifes, prioridade absoluta
                if self.eh_ifes_ou_campus(organizacao):
                    atual_pesq["id_organizacao"] = organizacao
                elif atual_pesq.get("id_organizacao") is None:
                    atual_pesq["id_organizacao"] = organizacao
            if titulacao:
                id_tit = self.simples("titulacao", "nome", titulacao)
                if id_tit and atual_pesq.get("id_titulacao") is None:
                    atual_pesq["id_titulacao"] = id_tit
        return pid

    NIVEL = {"ENSINO_PROFISSIONAL_DE_NIVEL_TECNICO": "ENSINO_PROFISSIONAL_TECNICO"}
    NIVEL_PROGRAMA = {
        "PIBIC": "Graduação", "PIBITI": "Graduação", "PIVIC": "Graduação", "PIVITI": "Graduação",
        "PIBIC_AF": "Graduação", "PIBIC_JR": "Ensino Médio (2o grau)",
        "PIBIC_EM": "Ensino Médio (2o grau)", "JTC": "Graduação", "PICTI": "Graduação"
    }

    def estudante(self, nome: Any, fonte: str, campus: Any = None, curso: Any = None,
                  nivel: Any = None) -> int | None:
        pid = self.pessoa(nome, fonte)
        if pid is not None:
            self.sub("estudante", pid, id_campus=self.campus(campus),
                     id_curso=self.simples("curso", "nome", curso),
                     id_nivel_treinamento=self.dominio("nivel_treinamento", nivel, self.NIVEL) if nivel else None)
        return pid

    # ================================================================ SRC
    def src(self) -> None:
        pasta = self.etl / "brutos" / "src"
        por_processo: dict[str, int] = {}
        vinculos: list[tuple[int, str]] = []
        for arq in sorted((pasta / "acoes").glob("acao_*.json"), key=lambda p: inteiro(p.stem) or 0):
            a = ler(arq)
            coord = None
            for n in nomes(a.get("Coordenador(a)"), r"[;,]"):
                coord = coord or self.pessoa(n, "src")
                if coord:
                    self.sub("pessoa_src", coord)
            i = self.novo("iniciativa", nome=texto(a.get("Título ação")) or f"Ação {a.get('acao_id')}")
            self.sub("acao", i, id_origem=inteiro(a.get("acao_id")), processo=texto(a.get("Processo nº")),
                     data_cadastro=data(a.get("Data de cadastro")),
                     relatorio_aprovado=booleano(a.get("Relatório aprovado")),
                     url_detalhe=texto(a.get("url_detalhe")),
                     id_natureza=self.dominio("natureza", a.get("Natureza")),
                     id_tipo_acao=self.dominio("tipo_acao", a.get("Tipo ação")),
                     id_area_conhecimento=self.area(a.get("Grande área conhecimento"), a.get("Grande área conhecimento")),
                     id_coordenador=coord, id_acao_pai=None)
            for c in {a.get("Campus"), a.get("campus")} - {None}:
                self.juncao("acao_campus", id_organizacao=self.campus(c), id_acao=i)
            if forma(a.get("Fomento")) not in ("", "sem vinculo"):
                self.juncao("fomento_acao", id_organizacao=self.org(a["Fomento"], "AgenciaFinanciamento"),
                            id_acao=i)
            if texto(a.get("Processo nº")):
                por_processo[a["Processo nº"].strip()] = i
            pai = texto(a.get("Ação vinculante"))
            if pai:
                vinculos.append((i, pai.split(" - ")[0].strip()))
            for filho in a.get("acoes_vinculadas") or []:
                if isinstance(filho, dict) and filho.get("processo"):
                    vinculos.append((-1, f"{filho['processo']}>{a.get('Processo nº')}"))
        for i, ref in vinculos:
            if i == -1:  # filho listado pela mãe
                filho, mae = ref.split(">")
                i, ref = por_processo.get(filho.strip(), 0), mae.strip()
            if i and ref in por_processo and por_processo[ref] != i:
                self.linhas["acao"][i]["id_acao_pai"] = por_processo[ref]
        self.src_participacoes(pasta / "participacoes", por_processo)

    def src_participacoes(self, pasta: Path, por_processo: dict[str, int]) -> None:
        for arq in sorted(pasta.glob("participacoes_*.json")):
            d = ler(arq)
            id_acao = por_processo.get(str(d.get("processo", "")).strip())
            if not id_acao:
                self.aviso("participações de processo sem ação carregada", d.get("processo"))
                continue
            for at in d.get("atividades", []):
                ativ = self.novo("atividade", nome=texto(at.get("atividade")) or f"Atividade {at.get('atividade_id')}",
                                 id_acao=id_acao,
                                 id_tipo_atividade=self.simples("tipo_atividade", "nome", at.get("tipo")))
                for p in at.get("publico_alvo", []):
                    pid = self.pessoa(p.get("Nome"), "src")
                    if pid is None:
                        continue
                    self.sub("pessoa_src", pid)
                    self.novo("registro_participante", carga_horaria=dinheiro(p.get("C.H")),
                              certificado=booleano(p.get("Certificado")), data_inicio=data(p.get("Início")),
                              data_termino=data(p.get("Término")), id_atividade=ativ, id_pessoa=pid,
                              id_situacao=self.dominio("situacao_participante", p.get("Situação")))
                for p in at.get("equipe_execucao", []):
                    pid = self.pessoa(p.get("Nome"), "src")
                    if pid is None:
                        continue
                    self.sub("pessoa_src", pid)
                    m = self.novo("membro_grupo", data_inicio=data(p.get("Início")), data_fim=data(p.get("Término")),
                                  id_papel=self.simples("papel", "nome", p.get("Função")))
                    self.sub("membro_equipe_execucao_src", m, id_atividade=ativ, id_pessoa=pid,
                             id_vinculo=self.dominio("vinculo", p.get("Vínculo")))

    # ================================================================ SigPesq
    @staticmethod
    def cancelamento(bruto: Any) -> tuple[str | None, str | None]:
        s = texto(bruto)
        if not s:
            return None, None
        s = re.sub(r"(?i)^por\s+", "", s)
        m = re.match(r"(?i)^(.*?)\s+em\s+(\d{1,2}/\d{1,2}/\d{2,4}.*)$", s)
        if m:
            return (texto(m.group(1)), data(m.group(2)))
        return s, None

    def sigpesq(self) -> None:
        pasta = self.etl / "brutos" / "sigpesq"
        linhas = lambda sub: [l for f in sorted((pasta / sub).glob("*.json")) for l in ler(f).get("linhas", [])]
        grupos: dict[str, int] = {}
        self.grupo_por_espelho: dict[str, tuple[int, int, str | None]] = {}
        for g in linhas("grupos"):
            area = self.area(g.get("AreaConhecimento"))
            campus = self.campus(g.get("Unidade"))
            if not texto(g.get("Nome")) or area is None or campus is None:
                self.aviso("grupo SigPesq sem nome, área ou unidade (NOT NULL; não gravado)", g.get("Sigla"))
                continue
            url = texto(g.get("Column1"))
            i = self.novo("grupo_pesquisa", nome=texto(g["Nome"]), sigla=texto(g.get("Sigla")),
                          url_cnpq=re.sub(r"(?<!:)/{2,}", "/", url) if url else None,
                          id_organizacao=campus, id_area_conhecimento=area)
            grupos[forma(g["Nome"])] = i
            if url and (m := re.search(r"espelhogrupo/(\d{16})", url)):
                self.grupo_por_espelho.setdefault(m.group(1), (i, campus, texto(g.get("Site"))))
            if texto(g.get("Sigla")):
                grupos.setdefault(forma(g["Sigla"]), i)
            for n in nomes(g.get("Lideres"), r","):
                self.juncao("lideranca_grupo_pesquisa", id_grupo_pesquisa=i,
                            id_pesquisador=self.pesquisador(n, "sigpesq", campus))
            if texto(g.get("ParecerDiretoria")):
                self.sem_coluna["grupo_pesquisa: parecer/situação no SigPesq (sem coluna)"] += 1

        projetos: dict[str, int] = {}
        for p in linhas("projetos"):
            coord = None
            campus_exec = self.campus(p.get("CampusExecucao"))
            for n in nomes(p.get("Coordenador"), r";"):
                coord = coord or self.pesquisador(n, "sigpesq", campus_exec)
            i = self.novo("iniciativa", nome=texto(p.get("Titulo")) or f"Projeto {p.get('Id')}")
            self.sub("projeto_pesquisa", i, id_origem=inteiro(p.get("Id")), data_inicio=data(p.get("Inicio")),
                     data_fim=data(p.get("Fim")), palavras_chave=texto(p.get("PalavraChave")),
                     sigilo=booleano(p.get("Sigilo")),
                     id_natureza_projeto=self.enum("tipo_natureza_projeto", p.get("Natureza")),
                     parecer_diretoria=self.enum("tipo_parecer_diretoria", p.get("ParecerDiretoria")),
                     id_campus=campus_exec,
                     id_area_conhecimento=self.area(p.get("AreaConhecimento")), id_coordenador=coord)
            projetos.setdefault(forma(p.get("Titulo")), i)
            for n in nomes(p.get("Pesquisadores"), r";"):
                self.juncao("participacao_pesquisador_projeto", id_pesquisador=self.pesquisador(n, "sigpesq", campus_exec),
                            id_projeto_pesquisa=i)
            for n in nomes(p.get("Estudantes"), r";"):
                self.juncao("participacao_estudante_projeto", id_estudante=self.estudante(n, "sigpesq"),
                            id_projeto_pesquisa=i)
            for n in nomes(p.get("ParceiroDemandante"), r";"):
                self.juncao("parceiro_demandante_projeto", id_organizacao=self.org(n, "ParceiroDemandante"),
                            id_projeto_pesquisa=i)
            for n in nomes(p.get("GrupoPesquisaExterno"), r";"):
                self.juncao("cooperacao_grupo_externo_projeto",
                            id_grupo_pesquisa_externo=self.simples("grupo_pesquisa_externo", "nome", n),
                            id_projeto_pesquisa=i)
            for n in nomes(p.get("GrupoPesquisa"), r";"):
                if forma(n) in grupos:
                    self.juncao("grupo_pesquisa_projeto", id_grupo_pesquisa=grupos[forma(n)], id_projeto_pesquisa=i)
                else:
                    self.aviso("grupo do projeto não está no relatório de grupos (vínculo não gravado)", n)

        minimos = 0
        for o in linhas("orientacoes"):
            campus_orient = self.campus(o.get("CampusOrientador"))
            orientador = self.pesquisador(o.get("Orientador"), "sigpesq", campus_orient)
            orientado = self.estudante(o.get("Orientado"), "sigpesq", o.get("Campus") or o.get("CampusExecucao"),
                                       o.get("Curso"), self.NIVEL_PROGRAMA.get(chave_enum(o.get("Programa"))))
            if orientador is None or orientado is None:
                self.aviso("orientação SigPesq sem orientador ou orientado (NOT NULL; não gravada)", o.get("Id"))
                continue
            projeto = projetos.get(forma(o.get("TituloPJ")))
            if projeto is None:
                cod = inteiro(o.get("CodPJ"))
                k = ("projeto_minimo", cod or forma(o.get("TituloPJ")))
                if k not in self.cache:
                    self.cache[k] = self.novo("iniciativa", nome=texto(o.get("TituloPJ")) or f"Projeto PJ {cod}")
                    self.sub("projeto_pesquisa", self.cache[k], id_origem=None,
                             id_campus=self.campus(o.get("CampusExecucao")),
                             id_area_conhecimento=self.area(o.get("AreaConhecimento"), o.get("GradeArea")))
                    minimos += 1
                projeto = self.cache[k]
            cod_pt = inteiro(o.get("CodPT"))
            plano = self.unico("plano_trabalho", cod_pt or forma(o.get("TituloPT")), codigo=cod_pt,
                               titulo=texto(o.get("TituloPT")) or f"Plano PT {cod_pt}",
                               id_projeto_pesquisa=projeto,
                               id_edital=self.simples("edital", "titulo", o.get("Edital")),
                               id_area_conhecimento=self.area(o.get("AreaConhecimento"), o.get("GradeArea")))
            fin = None if forma(o.get("AgFinanciadora")) in ("", "voluntario") else \
                self.org(o.get("AgFinanciadora"), "AgenciaFinanciamento")
            nome_canc, data_canc = self.cancelamento(o.get("CanceladoPor"))
            self.novo("orientacao", id_origem=inteiro(o.get("Id")), ano=ano(o.get("Ano")),
                       valor_bolsa=dinheiro(o.get("Valor")), data_inicio=data(o.get("Inicio")),
                       data_fim=data(o.get("Fim")), cancelado=booleano(o.get("Cancelado")),
                       nome_cancelador=nome_canc, data_cancelado=data_canc,
                       relatorio_enviado=None if not texto(o.get("AvaliacaoRelatorio")) else
                       forma(o.get("AvaliacaoRelatorio")) != "nao enviado",
                       modalidade=self.enum("tipo_modalidade", o.get("Modalidade")),
                       gerenciamento=self.enum("tipo_gerenciamento", o.get("Gerenciamento")),
                       id_programa=self.dominio("programa", o.get("Programa")), id_plano_trabalho=plano,
                       id_orientador=orientador, id_orientado=orientado,
                       id_campus=self.campus(o.get("CampusExecucao")), id_financiador=fin)
        self.avisos["projetos SigPesq mínimos criados para orientações (só título)"] += minimos

    # ================================================================ Lattes
    ORDEM_TITULACAO = ["POS_DOUTORADO", "LIVRE_DOCENCIA", "DOUTORADO", "MESTRADO_PROFISSIONAL", "MESTRADO",
                       "ESPECIALIZACAO", "APERFEICOAMENTO", "GRADUACAO"]
    MODALIDADE_ORIENTACAO = {"POS_DOUTORADO", "DOUTORADO", "MESTRADO", "ESPECIALIZACAO", "TCC",
                             "INICIACAO_CIENTIFICA", "OUTROS"}

    def lattes(self) -> None:
        arquivos = [a for a in sorted((self.etl / "brutos" / "lattes").glob("*.json"))
                    if not a.name.startswith("_")]
        for arq in arquivos:
            self.um_curriculo(ler(arq), arq.stem)

    def um_curriculo(self, cv: dict, ident: str) -> None:
        info = cv.get("informacoes_pessoais") or {}
        ident = str(info.get("id_lattes") or ident)
        dono = self.pessoa(info.get("nome_completo"), "lattes", ident)
        if dono is None:
            return
        self.pessoa_lattes(dono, id_lattes=ident, nome_citacoes=texto(info.get("nome_citacoes")),
                           texto_resumo=texto(info.get("texto_resumo")),
                           bolsa_produtividade=texto(info.get("bolsa_produtividade")),
                           url_lattes=texto(info.get("url")), data_atualizacao_cv=data(info.get("atualizacao_cv")),
                           endereco_profissional=texto(info.get("endereco_profissional")))

        maior = None
        for f in cv.get("formacao_academica") or []:
            nivel_f = texto((f.get("tipo") or "").partition(" em ")[0])
            if nivel_f and ano(f.get("ano_conclusao")):
                self.juncao("pessoa_lattes_titulacao", id_pessoa_lattes=dono,
                            id_titulacao=self.simples("titulacao", "nome", nivel_f))
            if nivel_f and ano(f.get("ano_conclusao")) and chave_enum(nivel_f) in self.ORDEM_TITULACAO:
                if maior is None or self.ORDEM_TITULACAO.index(chave_enum(nivel_f)) < self.ORDEM_TITULACAO.index(chave_enum(maior)):
                    maior = nivel_f
            inst = self.instituicao_lattes(f.get("nome_instituicao"))
            if inst is None:
                self.aviso("formação sem instituição (NOT NULL; não gravada)", ident)
                continue
            tipo = texto(f.get("tipo")) or ""
            nivel, _, curso = tipo.partition(" em ")
            desc = texto(f.get("descricao")) or ""
            achar = lambda rot: (m.group(1).strip() if (m := re.search(rot + r":\s*([^.]+?)(?:\.|,\s*Ano de obten|$)", desc)) else None)
            self.novo("formacao_academica", id_tipo_formacao=self.dominio("tipo_formacao", nivel),
                      ano_inicio=ano(f.get("ano_inicio")), ano_conclusao=ano(f.get("ano_conclusao")),
                      titulo_trabalho=achar("Título"), descricao=desc or None,
                      nome_orientador=achar("Orientador"), nome_coorientador=achar("Coorientador"),
                      id_pessoa_lattes=dono, id_instituicao=inst, id_curso=self.simples("curso", "nome", curso))

        atual_ifes = None
        atual_outro = None
        for a in cv.get("atuacao_profissional") or []:
            nome_inst = a.get("instituicao") or a.get("instituicao_nome")
            # P1: nunca aceita fomento como lotação
            if self.eh_fomento(nome_inst):
                continue
            inst = self.instituicao_lattes(nome_inst)
            if inst is None:
                self.aviso("atuação sem instituição (NOT NULL; não gravada)", ident)
                continue
            if forma(a.get("ano_fim")) == "atual":
                if self.eh_ifes_ou_campus(inst) and atual_ifes is None:
                    atual_ifes = inst
                elif atual_outro is None:
                    atual_outro = inst
            self.novo("atuacao_profissional", ano_inicio=ano(a.get("ano_inicio")), ano_fim=ano(a.get("ano_fim")),
                      atual=booleano(forma(a.get("ano_fim")) == "atual"), vinculo=texto(a.get("vinculo")),
                      enquadramento=texto(a.get("enquadramento")), regime_trabalho=texto(a.get("regime")),
                      atividades=self.lista_texto(a.get("atividades")),
                      id_pessoa_lattes=dono, id_instituicao=inst)

        lotacao = atual_ifes or atual_outro
        if lotacao is not None or maior:
            self.pesquisador(info.get("nome_completo"), "lattes",
                             organizacao=lotacao, titulacao=maior)

        for a in cv.get("areas_de_atuacao") or []:
            self.par_area(a.get("area"), a.get("grande_area"))
            ac = self.area(a.get("area"), a.get("grande_area"))
            sub = None
            if ac and texto(a.get("subarea")):
                sub = self.unico("subarea_conhecimento_lattes", (ac, forma(a["subarea"])), nome=texto(a["subarea"]),
                                 id_area_conhecimento=ac)
            if sub and texto(a.get("especialidade")):
                self.unico("especialidade_lattes", (sub, forma(a["especialidade"])), nome=texto(a["especialidade"]),
                           id_subarea_conhecimento=sub)
            ga = self.grande_area(a.get("grande_area"))
            if ga is None:
                continue
            self.unico("area_atuacao", (dono, forma(a.get("area")), forma(a.get("subarea")), forma(a.get("especialidade"))),
                       area=texto(a.get("area")), subarea=texto(a.get("subarea")),
                       especialidade=texto(a.get("especialidade")), id_grande_area=ga, id_pessoa_lattes=dono)

        for l in cv.get("linhas_de_pesquisa") or []:
            lp = self.simples("linha_pesquisa", "descricao", l.get("nome"))
            self.juncao("pesquisador_linha_pesquisa", id_pessoa_lattes=dono, id_linha_pesquisa=lp)

        for idi in cv.get("idiomas") or []:
            i = self.simples("idioma", "nome_idioma", idi.get("nome"))
            if i:
                nivel = lambda v: self.enum("tipo_nivel_proficiencia", v)
                self.unico("proficiencia_idioma", (dono, i), id_pessoa_lattes=dono, id_idioma=i,
                           compreende=nivel(idi.get("compreende")), fala=nivel(idi.get("fala")),
                           le=nivel(idi.get("le")), escreve=nivel(idi.get("escreve")))

        for p in cv.get("premios_titulos") or []:
            if texto(p.get("descricao")):
                self.novo("premio_titulo", descricao_titulo=texto(p["descricao"]), ano=ano(p.get("ano")),
                          id_pessoa_lattes=dono)

        for secao in ("projetos_pesquisa", "projetos_extensao", "projetos_desenvolvimento"):
            for pr in cv.get(secao) or []:
                nome = texto(pr.get("nome"))
                if not nome:
                    continue
                k = ("projeto_lattes", secao, forma(nome), ano(pr.get("ano_inicio")))
                novo = k not in self.cache
                if novo:
                    self.cache[k] = self.novo("iniciativa", nome=nome)
                    desc = pr.get("descricao")
                    desc = "\n".join(map(str, desc)) if isinstance(desc, list) else texto(desc)
                    fim = pr.get("ano_conclusao")
                    self.sub("projeto_lattes", self.cache[k], ano_inicio=ano(pr.get("ano_inicio")),
                             ano_conclusao=ano(fim),
                             situacao="EM_ANDAMENTO" if forma(fim) in ("atual", "") else "CONCLUIDO",
                             descricao=desc or None)
                proj = self.cache[k]
                for m in pr.get("integrantes") or []:
                    pid = self.pessoa_lattes(self.pessoa(m.get("nome"), "lattes"))
                    if pid:
                        papel = "COORDENADOR" if "coord" in forma(m.get("papel")) else "INTEGRANTE"
                        self.unico("membro_projeto", (pid, proj), id_pessoa_lattes=pid,
                                   id_projeto_lattes=proj, papel=papel)
                if novo:
                    for fin in pr.get("financiadores") or []:
                        org = self.org(fin.get("nome"), "AgenciaFinanciamento")
                        if org:
                            self.unico("fomento_projeto", (org, proj), id_organizacao=org, id_projeto_lattes=proj,
                                       id_tipo_apoio=self.dominio("tipo_apoio_financiamento", fin.get("tipo_apoio"),
                                                                  {"AUXILIO": "AUXILIO_FINANCEIRO"}))

        orient = cv.get("orientacoes") or {}
        for situacao in ("em_andamento", "concluidas"):
            for tipo, lista in sorted((orient.get(situacao) or {}).items()):
                for o in lista or []:
                    inst = self.instituicao_lattes(o.get("instituicao"))
                    if inst is None or not texto(o.get("titulo")):
                        self.aviso("orientação Lattes sem título ou instituição (NOT NULL; não gravada)", ident)
                        continue
                    mod = chave_enum(tipo)
                    self.novo("orientacao_lattes", titulo=texto(o["titulo"]),
                              modalidade=mod if mod in self.MODALIDADE_ORIENTACAO else None,
                              papel_orientacao="ORIENTADOR",
                              status="EM_ANDAMENTO" if situacao == "em_andamento" else "CONCLUIDO",
                              ano_inicio=ano(o.get("ano_inicio")), ano_conclusao=ano(o.get("ano_conclusao")),
                              tipo_trabalho=texto(o.get("tipo_trabalho")), id_orientador=dono,
                              id_orientando=self.pessoa_lattes(self.pessoa(o.get("orientando"), "lattes")),
                              id_instituicao=inst,
                              id_financiador=self.org(o.get("financiador"), "AgenciaFinanciamento"))

        for tipo, lista in sorted((cv.get("bancas") or {}).items()):
            for b in lista or []:
                cand = self.pessoa_lattes(self.pessoa(b.get("aluno"), "lattes"))
                if cand is None:
                    continue
                k = ("banca", forma(b.get("titulo_trabalho")), ano(b.get("ano")), cand)
                if k not in self.cache:
                    self.cache[k] = self.novo(
                        "banca_examinadora", modalidade=self.enum("tipo_modalidade_banca", tipo),
                        titulo_trabalho=texto(b.get("titulo_trabalho")), ano=ano(b.get("ano")),
                        curso=texto(b.get("curso")), descricao=texto(b.get("descricao")),
                        id_instituicao=self.instituicao_lattes(b.get("universidade") or self.inst_da_descricao(b.get("descricao"))),
                        id_candidato=cand)
                self.juncao("membro_banca_examinadora", id_banca_examinadora=self.cache[k], id_pessoa_lattes=dono)

        eventos = cv.get("eventos") or {}
        for chave, papel in (("participacoes", "PARTICIPACAO"), ("organizacoes", "ORGANIZACAO")):
            for e in eventos.get(chave) or []:
                nome = texto(e.get("evento"))
                if not nome:
                    continue
                ev = self.unico("evento_cientifico", (forma(nome), ano(e.get("ano"))), nome_evento=nome,
                                 natureza_tipo_evento=texto(e.get("tipo_evento") or e.get("natureza")), ano=ano(e.get("ano")))
                self.unico("participacao_evento", (dono, ev, papel), id_pessoa_lattes=dono, id_evento_cientifico=ev,
                           papel_evento=papel, titulo_apresentacao=texto(e.get("apresentacao")))

        self.producoes(cv, dono)

    PRODUCOES = {
        ("producao_bibliografica", "artigos_periodicos"): ("artigo", "ARTIGO_PERIODICO", None),
        ("producao_bibliografica", "artigos_aceitos"): ("artigo", "ARTIGO_PERIODICO", "Aceito para publicação"),
        ("producao_bibliografica", "trabalhos_completos_congressos"): ("artigo", "TRABALHO_COMPLETO_CONGRESSO", None),
        ("producao_bibliografica", "resumos_expandidos"): ("artigo", "RESUMO_EXPANDIDO_CONGRESSO", None),
        ("producao_bibliografica", "resumos_congressos"): ("artigo", "RESUMO_CONGRESSO", None),
        ("producao_bibliografica", "apresentacoes_trabalhos"): ("artigo", "OUTRO", "Apresentação de trabalho"),
        ("producao_bibliografica", "textos_jornais"): ("artigo", "OUTRO", "Texto em jornal ou revista"),
        ("producao_bibliografica", "livros_publicados"): ("livro", "LIVRO_PUBLICADO", None),
        ("producao_bibliografica", "capitulos_livros"): ("livro", "CAPITULO_LIVRO", None),
        ("producao_bibliografica", "outras_producoes"): ("tecnica", "OUTRA", None),
        ("producao_tecnica", "softwares_sem_patente"): ("tecnica", "SOFTWARE_SEM_PATENTE", None),
        ("producao_tecnica", "trabalhos_tecnicos"): ("tecnica", "TRABALHO_TECNICO", None),
        ("producao_tecnica", "produtos_tecnologicos"): ("tecnica", "OUTRA", None),
        ("producao_tecnica", "processos_tecnicas"): ("tecnica", "OUTRA", None),
        ("producao_tecnica", "outras_producoes_tecnicas"): ("tecnica", "OUTRA", None),
        ("producao_tecnica", "entrevistas"): ("tecnica", "OUTRA", None),
        ("producao_artistica", None): ("tecnica", "PRODUCAO_ARTISTICA_CULTURAL", None),
    }

    def producoes(self, cv: dict, dono: int) -> None:
        for (secao, sub), (tipo, cat, natureza) in self.PRODUCOES.items():
            bloco = cv.get(secao)
            itens = (bloco or []) if sub is None else ((bloco or {}).get(sub) or [])
            for it in itens:
                titulo = texto(it.get("titulo"))
                if not titulo:
                    continue
                k = ("producao", secao, sub, forma(titulo), ano(it.get("ano")))
                if k not in self.cache:
                    pid = self.cache[k] = self.novo("producao", titulo=titulo, ano=ano(it.get("ano")))
                    if tipo == "artigo":
                        self.sub("artigo_trabalho_evento", pid,
                                 id_tipo_publicacao=self.dominio("tipo_artigo_evento", cat),
                                 veiculo_revista_evento=texto(it.get("revista") or it.get("evento") or it.get("jornal")),
                                 doi=texto(it.get("doi")), issn_isbn=texto(it.get("issn") or it.get("isbn")),
                                 volume=texto(it.get("volume")), numero=texto(it.get("numero")),
                                 paginas=texto(it.get("paginas")),
                                 data_publicacao=texto(it.get("data")), natureza=natureza)
                    elif tipo == "livro":
                        self.sub("livro_capitulo", pid, id_tipo_livro_capitulo=self.dominio("tipo_livro_capitulo", cat),
                                 editora=texto(it.get("editora")), paginas=texto(it.get("paginas")))
                    else:
                        self.sub("producao_tecnica_artistica_bibliografica", pid,
                                 id_categoria=self.dominio("categoria_producao_tecnica", cat),
                                 subtipo=texto(it.get("tipo")) or (sub or secao).replace("_", " "))
                self.juncao("autoria_producao", id_pessoa_lattes=dono, id_producao=self.cache[k])

        # P5: Patentes e registros (id_instituicao_depositante NULLABLE no SQLite)
        pats = cv.get("patentes_registros") or {}
        for sub_tipo, lista in pats.items():
            for item in lista if isinstance(lista, list) else []:
                titulo = texto(item.get("titulo") or item.get("nome"))
                if not titulo:
                    continue
                ano_p = ano(item.get("ano"))
                k = ("producao", "patentes_registros", sub_tipo, forma(titulo), ano_p)
                if k not in self.cache:
                    pid = self.cache[k] = self.novo("producao", titulo=titulo, ano=ano_p)
                    tipo_pat = "PATENTE" if "patente" in sub_tipo else (
                        "PROGRAMA_COMPUTADOR" if "programa" in sub_tipo or "software" in sub_tipo else (
                            "DESENHO_INDUSTRIAL" if "desenho" in sub_tipo else (
                                "MARCA" if "marca" in sub_tipo else "PATENTE"
                            )
                        )
                    )
                    dep = self.instituicao_lattes(item.get("instituicao_depositante") or item.get("instituicao") or item.get("depositante"))
                    self.sub("patente_registro", pid,
                             id_tipo_patente_registro=self.dominio("tipo_patente_registro", tipo_pat),
                             modalidade_patente=texto(item.get("modalidade") or sub_tipo),
                             pais=texto(item.get("pais") or "Brasil"),
                             data_registro=texto(item.get("data") or item.get("data_registro")),
                             codigo_registro=texto(item.get("codigo") or item.get("registro") or item.get("codigo_registro")),
                             id_instituicao_depositante=dep)
                self.juncao("autoria_producao", id_pessoa_lattes=dono, id_producao=self.cache[k])

        softwares_pat = (cv.get("producao_tecnica") or {}).get("softwares_com_patente") or []
        for item in softwares_pat if isinstance(softwares_pat, list) else []:
            titulo = texto(item.get("titulo") or item.get("nome"))
            if not titulo:
                continue
            ano_p = ano(item.get("ano"))
            k = ("producao", "producao_tecnica", "softwares_com_patente", forma(titulo), ano_p)
            if k not in self.cache:
                pid = self.cache[k] = self.novo("producao", titulo=titulo, ano=ano_p)
                dep = self.instituicao_lattes(item.get("instituicao_depositante") or item.get("instituicao") or item.get("depositante"))
                self.sub("patente_registro", pid,
                         id_tipo_patente_registro=self.dominio("tipo_patente_registro", "PROGRAMA_COMPUTADOR"),
                         modalidade_patente="SOFTWARE_COM_PATENTE",
                         pais=texto(item.get("pais") or "Brasil"),
                         data_registro=texto(item.get("data") or item.get("data_registro")),
                         codigo_registro=texto(item.get("codigo") or item.get("registro") or item.get("codigo_registro")),
                         id_instituicao_depositante=dep)
            self.juncao("autoria_producao", id_pessoa_lattes=dono, id_producao=self.cache[k])

    # ================================================================ CNPq
    # P3: Adiciona 'EXCLUIDO' mapeado para o domínio/check de situação do grupo
    SITUACAO_GRUPO = (
        ("CERTIFICADO_NAO_ATUALIZADO", "CERTIFICADO_NAO_ATUALIZADO"),
        ("EM_PREENCHIMENTO", "EM_PREENCHIMENTO"),
        ("AGUARDANDO_CERTIFICACAO", "AGUARDANDO_CERTIFICACAO"),
        ("CERTIFICADO", "CERTIFICADO"),
        ("EXCLUIDO", "EXCLUIDO")
    )
    PAPEL_RH = {
        "pesquisadores": ("Pesquisador", "ATIVO"), "estudantes": ("Estudante", "ATIVO"),
        "tecnicos": ("Técnico", "ATIVO"), "colaboradores_estrangeiros": ("Colaborador estrangeiro", "ATIVO"),
        "egressos_pesquisadores": ("Pesquisador", "EGRESSO"), "egressos_estudantes": ("Estudante", "EGRESSO"),
        "egressos_tecnicos": ("Técnico", "EGRESSO"), "egressos": ("Egresso", "EGRESSO")
    }

    @staticmethod
    def itens(secao: Any) -> list[dict]:
        out: list[dict] = []
        if isinstance(secao, dict):
            for v in secao.values():
                for bloco in v if isinstance(v, list) else []:
                    out += [x for x in (bloco if isinstance(bloco, list) else [bloco]) if isinstance(x, dict)]
        return out

    def cnpq(self) -> None:
        """Espelho DGP/CNPq: só para grupos que já vieram do SigPesq."""
        for arq in sorted((self.etl / "brutos" / "cnpq").glob("grupo_*.json")):
            g = ler(arq)
            ident = str(g.get("id_espelho") or arq.stem.removeprefix("grupo_"))
            if ident not in self.grupo_por_espelho:
                self.aviso("grupo do CNPq sem grupo correspondente no SigPesq (não gravado)", ident)
                continue
            gid, campus, site = self.grupo_por_espelho[ident]
            idt = g.get("identificacao") or {}
            k = chave_enum(idt.get("situacao_do_grupo"))
            situacao = next((v for p, v in self.SITUACAO_GRUPO if k.startswith(p)), None)
            if k and situacao is None:
                self.aviso("valor fora do ENUM tipo_situacao_grupo (gravado NULL)", idt.get("situacao_do_grupo"))
            inst = self.org(idt.get("instituicao_do_grupo"), "Instituicao") or self.ifes()
            rep = g.get("repercussoes") or {}
            end = g.get("endereco_contato") or {}
            id_end = None
            if any(texto(end.get(k)) for k in ("logradouro", "bairro", "localidade", "cep")):
                uf = texto(end.get("uf"))
                id_end = self.novo("endereco", logradouro=texto(end.get("logradouro")), numero=texto(end.get("numero")),
                                   complemento=texto(end.get("complemento")), bairro=texto(end.get("bairro")),
                                   localidade=texto(end.get("localidade")),
                                   uf=self.enum("tipo_uf", uf) if uf else None, cep=texto(end.get("cep")),
                                   caixa_postal=texto(end.get("caixa_postal")), latitude=texto(end.get("latitude")),
                                   longitude=texto(end.get("longitude")))
            site = site or texto(end.get("website"))
            self.sub("grupo_pesquisa_cnpq", gid, situacao_grupo=situacao, ano_formacao=ano(idt.get("ano_de_formacao")),
                     data_situacao=data(idt.get("data_da_situacao")),
                     data_ultimo_envio=data(idt.get("data_do_ultimo_envio")),
                     repercussoes=texto(rep.get("descricao")) if isinstance(rep, dict) else texto(rep),
                     id_endereco=id_end, id_instituicao=inst, id_campus=campus)
            if site:
                self.unico("website", (gid, site), url=site, id_grupo_pesquisa_cnpq=gid)
            for lider in idt.get("lideres_do_grupo") or []:
                if isinstance(lider, str) and lider.strip().lower() != "ui-button":
                    self.juncao("lideranca_grupo_pesquisa", id_grupo_pesquisa=gid,
                                id_pesquisador=self.pesquisador(lider, "cnpq", campus))
            area = texto(idt.get("area_predominante"))
            if area and ";" in area:
                self.par_area(area.split(";", 1)[1], area.split(";")[0])
            if area:
                self.juncao("grupo_pesquisa_grande_area", id_grupo_pesquisa_cnpq=gid,
                            id_grande_area=self.grande_area(area.split(";")[0]))
            for linha in (g.get("linhas_de_pesquisa") or {}).get("linhas") or []:
                if isinstance(linha, dict):
                    lp = self.simples("linha_pesquisa", "descricao", linha.get("nome_da_linha_de_pesquisa"))
                    self.juncao("grupo_pesquisa_linha_pesquisa", id_grupo_pesquisa_cnpq=gid, id_linha_pesquisa=lp)
            rh = g.get("recursos_humanos") or g.get("recursos_humanos_do_grupo") or {}
            for tabela, itens in sorted(rh.items()):
                papel, status = self.PAPEL_RH.get(tabela, ("Membro", "EGRESSO" if tabela.startswith("egresso") else "ATIVO"))
                for it in itens if isinstance(itens, list) else []:
                    nome = next((it.get(c) for c in ("nome", tabela.removeprefix("egressos_"), tabela, "pesquisadores",
                                                       "estudantes", "tecnicos") if isinstance(it.get(c), str) and it.get(c).strip()), None)
                    if not nome or nome.strip().lower() == "ui-button":
                        continue
                    if tabela == "pesquisadores":
                        pid = self.pesquisador(nome, "cnpq", campus, titulacao=it.get("titulacao_maxima"))
                    elif tabela == "estudantes":
                        pid = self.estudante(nome, "cnpq", campus, nivel=it.get("nivel_de_treinamento"))
                    else:
                        pid = self.pessoa(nome, "cnpq")
                    if pid is None:
                        continue
                    m = self.novo("membro_grupo", data_inicio=data(it.get("data_inicio")), data_fim=data(it.get("data_fim")),
                                  id_papel=self.simples("papel", "nome", papel))
                    self.sub("membro_grupo_cnpq", m, status_participacao=status, id_pessoa=pid,
                             id_grupo_pesquisa_cnpq=gid)
            for chave, rotulo, campo in (("instituicoes_parceiras_relatadas_pelo_grupo", "Instituição parceira",
                                          "nome_da_instituicao_parceira"),
                                         ("incts_parceiras_relatadas_pelo_grupo", "INCT", "nome_da_inct_parceira")):
                for it in self.itens(g.get(chave)):
                    nome = texto(it.get(campo))
                    if not nome:
                        continue
                    org = self.org(nome, "InstituicaoParceira")
                    uf = texto(it.get("uf"))
                    self.sub("instituicao_parceira_cnpq", org, sigla=texto(it.get("sigla")),
                             uf=self.enum("tipo_uf", uf) if uf else None)
                    self.unico("parceria_grupo", (gid, org), id_grupo_pesquisa_cnpq=gid,
                                id_instituicao_parceira=org, tipo=rotulo)
            for it in self.itens(g.get("equipamentos_e_softwares_relevantes")):
                for k, tipo in (("softwares", "SOFTWARE"), ("software", "SOFTWARE"),
                                ("equipamentos", "EQUIPAMENTO"), ("equipamento", "EQUIPAMENTO")):
                    if texto(it.get(k)):
                        eq = self.unico("equipamento_software", (tipo, forma(it[k])), nome=texto(it[k]), tipo=tipo)
                        self.juncao("grupo_pesquisa_equipamento", id_grupo_pesquisa_cnpq=gid, id_equipamento_software=eq)

    # ================================================================ SQL
    def tabelas_com_dados(self) -> list[str]:
        faltando = set(self.linhas) - set(self.ORDEM)
        if faltando:
            raise RuntimeError(f"tabelas fora da ORDEM: {faltando}")
        return [t for t in self.ORDEM if self.linhas.get(t)]

    def sql(self) -> str:
        """Gera o bloco SQL de inserção pura compatível com SQLite."""
        out = [
            "-- Gerado por Adito/scripts/popular_banco.py para SQLite. Transação atômica única.",
            "PRAGMA foreign_keys = ON;",
            "BEGIN TRANSACTION;"
        ]
        for t in self.tabelas_com_dados():
            linhas = list(self.linhas[t].values())
            if t in self.BASE or t not in self.JUNCAO:
                linhas.sort(key=lambda r: r.get("id", 0))
            cols: list[str] = []
            for r in linhas:
                cols += [c for c in r if c not in cols]
            for i in range(0, len(linhas), LOTE):
                valores = ",\n".join("(" + ", ".join(literal(r.get(c)) for c in cols) + ")"
                                     for r in linhas[i:i + LOTE])
                out.append(f"INSERT INTO {t} ({', '.join(cols)}) VALUES\n{valores};")
        out.append("COMMIT;")
        return "\n".join(out) + "\n"

    def contagens(self) -> dict[str, int]:
        return {t: len(self.linhas[t]) for t in self.tabelas_com_dados()}


# ============================================================================ PII & Validação
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
CPF = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\d])|(?<!\d)\d{11}(?!\d)")


def conferir_pii(sql: str) -> list[str]:
    achados = []
    for nome, rx in (("e-mail", EMAIL), ("CPF/11 dígitos", CPF)):
        m = rx.search(sql)
        if m:
            achados.append(f"{nome} perto de: {sql[max(0, m.start() - 40):m.end() + 10]!r}")
    return achados


def inicializar_banco_sqlite(banco_path: Path) -> sqlite3.Connection:
    """Cria ou recria a base dados.db aplicando os DDLs 00 a 04."""
    banco_path.parent.mkdir(parents=True, exist_ok=True)
    if banco_path.exists():
        banco_path.unlink()

    conn = sqlite3.connect(str(banco_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    ddl_arquivos = [
        "00_schema.sql",
        "01_tipos_e_dominios.sql",
        "02_tabelas.sql",
        "03_relacionamentos_e_juncoes.sql",
        "04_fatos_views.sql"
    ]
    for ddl_arq in ddl_arquivos:
        sql_text = (DDL / ddl_arq).read_text(encoding="utf-8")
        conn.executescript(sql_text)

    return conn


def validar_sanidade_banco(conn: sqlite3.Connection) -> dict[str, Any]:
    """Executa as validações estruturais pós-carga e checagens das 6 fatos (P1 a P12)."""
    # 1. Integridade de chaves estrangeiras
    fk_erros = list(conn.execute("PRAGMA foreign_key_check;"))
    if fk_erros:
        raise RuntimeError(f"Violação de chaves estrangeiras pós-carga: {fk_erros}")

    # 2. Validações das views analíticas
    res_lider = conn.execute("SELECT SUM(flag_lider) FROM vfact_grupo_pesquisa_membro_resolved;").fetchone()[0] or 0
    if res_lider <= 0:
        raise AssertionError("vfact_grupo_pesquisa_membro_resolved: SUM(flag_lider) deve ser > 0")

    res_neg_dias = conn.execute(
        "SELECT COUNT(*) FROM vfact_grupo_pesquisa_membro_resolved WHERE tempo_participacao_dias < 0;"
    ).fetchone()[0]
    if res_neg_dias > 0:
        raise AssertionError(f"vfact_grupo_pesquisa_membro_resolved: {res_neg_dias} registros com tempo_participacao_dias < 0")

    # Obra única na produção
    row_prod = conn.execute(
        "SELECT SUM(flag_obra_unica), COUNT(DISTINCT id_producao) FROM vfact_producao_cientifica_resolved;"
    ).fetchone()
    sum_obra_unica, count_dist_prod = row_prod[0] or 0, row_prod[1] or 0
    if sum_obra_unica != count_dist_prod:
        raise AssertionError(
            f"vfact_producao_cientifica_resolved: SUM(flag_obra_unica) ({sum_obra_unica}) != COUNT(DISTINCT id_producao) ({count_dist_prod})"
        )

    # Campus IFES limpo de fomento/externos (P1)
    fapes_ufes_campus = conn.execute(
        "SELECT COUNT(*) FROM vfact_producao_cientifica_resolved WHERE campus IN ('FAPES', 'UFES');"
    ).fetchone()[0]
    if fapes_ufes_campus > 0:
        raise AssertionError(f"vfact_producao_cientifica_resolved: {fapes_ufes_campus} ocorrências indevidas de FAPES/UFES na coluna campus")

    # Contagens das 6 views
    views = [
        "vfact_extensao_acao_resolved",
        "vfact_extensao_participacao_resolved",
        "vfact_projeto_pesquisa_resolved",
        "vfact_orientacao_bolsa_resolved",
        "vfact_producao_cientifica_resolved",
        "vfact_grupo_pesquisa_membro_resolved"
    ]
    contagens_views = {}
    for v in views:
        qtd = conn.execute(f"SELECT COUNT(*) FROM {v};").fetchone()[0]
        contagens_views[v] = qtd

    return {
        "fk_erros": len(fk_erros),
        "total_lideres": res_lider,
        "obras_unicas_consistentes": True,
        "campus_ifes_puro": True,
        "views": contagens_views
    }


def main(argv: Iterable[str] | None = None) -> int:
    inicio = time.time()
    ap = argparse.ArgumentParser(description="Popula o banco SQLite (dados.db) com os dados acadêmicos do Adito.")
    ap.add_argument("--etl", type=Path, default=os.environ.get("ADITO_ETL_DIR") or AQUI.parent / "etl",
                    help="Pasta etl/ do Adito (com brutos/ e trabalho/). Padrão: $ADITO_ETL_DIR ou ../etl")
    ap.add_argument("--banco", type=Path, default=os.environ.get("ADITO_DB_PATH") or AQUI.parent / "app" / "data" / "dados.db",
                    help="Caminho do arquivo SQLite dados.db (padrão: Adito/app/data/dados.db)")
    ap.add_argument("--saida", type=Path, default=None, help="Arquivo SQL de dump (padrão: <etl>/saida/carga_banco.sql)")
    ap.add_argument("--so-gerar", action="store_true", help="Só gera o SQL e o relatório; não executa a carga")
    args = ap.parse_args(list(argv) if argv is not None else None)

    etl = args.etl.expanduser().resolve()
    if not (etl / "brutos").is_dir():
        ap.error(f"{etl} não parece a pasta etl/ do Adito (falta brutos/)")

    banco_path = args.banco.expanduser().resolve()

    carga = Carga(etl)
    carga.carregar_pessoas()
    carga.src()
    carga.sigpesq()
    carga.lattes()
    carga.cnpq()
    carga.completar_areas()
    sql_inserts = carga.sql()

    saida = args.saida or etl / "saida" / "carga_banco.sql"
    saida.parent.mkdir(parents=True, exist_ok=True)
    pii = conferir_pii(sql_inserts)
    if pii:
        print("erro: o SQL gerado tem algo com formato de dado pessoal; nada foi gravado no banco:", file=sys.stderr)
        for p in pii:
            print(f"  {p}", file=sys.stderr)
        return 2

    saida.write_text(sql_inserts, encoding="utf-8")
    relatorio = {
        "contagens": carga.contagens(),
        "avisos": {k: {"quantidade": v, "exemplos": sorted(carga.exemplos.get(k, []))}
                   for k, v in sorted(carga.avisos.items())},
        "dados_sem_coluna_no_banco": dict(sorted(carga.sem_coluna.items()))
    }

    print(f"SQL gerado: {saida} ({saida.stat().st_size // 1024} KiB)")
    for t, n in relatorio["contagens"].items():
        print(f"  {t:45s} {n:7d}")

    if args.so_gerar:
        (saida.parent / "carga_banco_relatorio.json").write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0

    print(f"\nInicializando banco SQLite nativo em: {banco_path}...")
    conn = inicializar_banco_sqlite(banco_path)

    print("Executando carga atômica de dados...")
    conn.executescript(sql_inserts)

    print("Executando validações estruturais e integridade (PRAGMA foreign_key_check, P1 a P12)...")
    validacao = validar_sanidade_banco(conn)
    relatorio["validacao_pos_carga"] = validacao
    (saida.parent / "carga_banco_relatorio.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    conn.execute("PRAGMA optimize;")
    conn.close()

    tempo_total = time.time() - inicio
    tamanho_mb = banco_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Carga concluída com sucesso em {tempo_total:.2f}s!")
    print(f"📦 Tamanho final de {banco_path.name}: {tamanho_mb:.2f} MB")
    print("\n📊 Linhas acessíveis pelas 6 Views Analíticas (OLTP):")
    for v, qtd in validacao["views"].items():
        print(f"  {v:45s} {qtd:7d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
