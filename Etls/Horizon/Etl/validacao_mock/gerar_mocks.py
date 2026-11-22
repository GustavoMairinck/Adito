#!/usr/bin/env python3
"""Gera 300 registros fictícios para validar o ETL do Horizon (issue #5 do Adito).

Fontes geradas (nas mesmas estruturas que o ETL lê):

* SigPesq – grupos (xlsx) ............ 28 registros
* SigPesq – projetos (xlsx) .......... 77 registros
* SigPesq – bolsistas (3 xlsx) ....... 120 registros
* Lattes – currículos (JSON) ......... 50 registros
* CNPq – espelhos de grupo (JSON) .... 25 registros
                                       ---
                                       300

Cada fonte tem casos válidos (caminho feliz) e casos de exceção (nulos,
formatos inválidos, duplicidades, referências quebradas). Junto com os dados é
gravado ``gabarito.json``: o estado esperado do banco para cada registro,
calculado aqui por uma simulação das regras documentadas do ETL (docstrings de
``src/core/logic/carga``) e, onde a regra de negócio é mais clara que o código,
pela expectativa de negócio (marcada como ``regra: "negocio"``).

Todos os nomes, e-mails, IDs Lattes e URLs são inventados (domínio ``.mock``).

Uso: python gerar_mocks.py --saida dados [--semente 20261014]
"""

import argparse
import csv
import json
import os
import random
import shutil
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from comum import chave_pessoa, data_br, iso, normalizar_texto, slug

HOJE = date.today()

# ---------------------------------------------------------------- vocabulário
PRIMEIROS = """Ana Bruno Carla Daniel Eduarda Felipe Gabriela Henrique Isabela João Karina
Lucas Mariana Nicolas Olívia Pedro Quésia Rafael Sabrina Tiago Úrsula Vinícius Wesley
Yasmin Zélia André Beatriz Caio Débora Enzo Fernanda Gustavo Helena Igor Júlia Kauã
Larissa Mateus Natália Otávio Paula Renan Sofia Thales Valéria Vitor Alice Bernardo
Cecília Diego Elisa Fábio Giovana Hugo Íris Jorge Lívia Marcelo Nathan Priscila""".split()
SOBRENOMES = """Silva Souza Oliveira Santos Pereira Lima Carvalho Ferreira Rodrigues Almeida
Costa Gomes Martins Araújo Barbosa Ribeiro Rocha Dias Moreira Nunes Mendes Freitas Cardoso
Teixeira Correia Pinto Vieira Monteiro Moura Cavalcanti Batista Campos Fonseca Rezende
Pacheco Tavares Siqueira Bezerra Macedo Coelho Duarte Lopes Ramos Farias Miranda Sales
Andrade Peixoto Queiroz Guimarães Brandão Xavier Prates Valadares Bragança Loureiro
Zanetti Bortolini Coutinho Falqueto""".split()
CAMPI = ["Serra", "Vitória", "Cariacica", "Colatina", "Linhares", "Guarapari",
         "Cachoeiro de Itapemirim", "Santa Teresa"]
AREAS = ["Ciência da Computação", "Engenharia Elétrica", "Matemática", "Química",
         "Educação", "Engenharia de Controle e Automação", "Física", "Letras",
         "Administração", "Ciências Biológicas", "Engenharia Ambiental", "Agronomia"]
TEMAS_GRUPO = ["Sistemas Inteligentes", "Robótica Educacional", "Energias Renováveis",
               "Química Analítica", "Ensino de Matemática", "Engenharia de Software",
               "Redes e Sistemas Distribuídos", "Automação Industrial", "Biotecnologia",
               "Linguagens e Culturas", "Gestão Pública", "Recursos Hídricos",
               "Agroecologia", "Física Aplicada", "Ciência de Dados", "Educação Inclusiva",
               "Materiais Avançados", "Internet das Coisas", "Processamento de Sinais",
               "Saúde Coletiva", "Visão Computacional", "Empreendedorismo e Inovação",
               "Metrologia", "Tecnologias Assistivas", "Segurança da Informação",
               "Geotecnologias", "Alimentos Funcionais", "Mobilidade Urbana"]
PALAVRAS = ["aprendizado de máquina", "sustentabilidade", "ensino", "IoT", "sensores",
            "inclusão", "dados abertos", "eficiência energética", "biomassa", "robótica",
            "visão computacional", "qualidade da água", "extensão tecnológica",
            "acessibilidade", "otimização", "metodologias ativas"]
ACOES = ["Desenvolvimento de", "Análise de", "Avaliação de", "Modelagem de",
         "Monitoramento de", "Otimização de", "Uso de", "Aplicação de", "Estudo de",
         "Implementação de"]
OBJETOS = ["sensores de baixo custo", "redes neurais", "algoritmos genéticos",
           "materiais didáticos", "sistemas embarcados", "biofiltros", "painéis solares",
           "dados abertos", "jogos educacionais", "robôs móveis", "compostos fenólicos",
           "microrredes", "plataformas web", "modelos preditivos",
           "resíduos agroindustriais"]
COMPLEMENTOS = ["para a agricultura familiar", "no ensino médio integrado",
                "em bacias hidrográficas do ES", "na indústria metalmecânica",
                "para acessibilidade", "na gestão escolar", "em ambientes hospitalares",
                "para cidades inteligentes", "no litoral capixaba",
                "em comunidades tradicionais"]
ACOES_PT = ["Coleta e tratamento de dados sobre", "Prototipação de", "Levantamento bibliográfico sobre",
            "Testes experimentais com", "Validação de", "Documentação técnica de",
            "Simulação computacional de", "Caracterização de"]
PARCEIROS = ["Prefeitura Municipal da Serra", "Secretaria de Estado da Educação",
             "Mock Tecnologia Ltda", "Escola Estadual Fictícia de Ensino Médio",
             "Cooperativa Agrícola Mock", "Associação de Moradores Mock"]
FINANCIAMENTOS = [  # programa, agência, valor como vem na planilha, valor esperado
    ("PIBIC", "CNPq", "700,00", 700.00),
    ("PIBITI", "CNPq", "700", 700.00),
    ("PIBIC", "FAPES", "600,00", 600.00),
    ("PIVIC", "Voluntário", "0", 0.00),
    ("PIBIC-EM", "CNPq", "100,00", 100.00),
    ("PIBIC", "IFES", "400,00", 400.00),
]
IDIOMAS = ["Inglês", "Espanhol", "Francês", "Italiano", "Alemão"]
NIVEIS = {"Bem": "alto", "Razoavelmente": "medio", "Pouco": "basico"}
VINCULOS = ["Servidor Público", "Celetista", "Bolsista", "Professor Visitante", "Colaborador"]
INSTITUICOES_ENSINO = ["Universidade Federal do Espírito Santo", "Universidade Federal de Minas Gerais",
                       "Universidade de São Paulo", "Universidade Estadual de Campinas",
                       "Universidade Federal do Rio de Janeiro", "Instituto Tecnológico de Aeronáutica"]
EMPRESAS = ["Mock Siderurgia S.A.", "Prefeitura Municipal de Vila Velha", "Secretaria Municipal de Saúde de Vitória",
            "Mock Software Ltda"]
REVISTAS = ["Revista Brasileira de Informática na Educação", "IEEE Latin America Transactions",
            "Química Nova", "Revista Brasileira de Ensino de Física", "Engenharia Sanitária e Ambiental",
            "Journal of Mock Studies"]
EVENTOS = ["Simpósio Brasileiro de Informática na Educação", "Congresso Brasileiro de Automática",
           "Jornada de Iniciação Científica do IFES", "Congresso Mock de Engenharia"]


def evitar_hoje(d: date) -> date:
    """Datas de fim longe de hoje, para a situação esperada não virar no dia seguinte."""
    if abs((d - HOJE).days) < 45:
        return d + timedelta(days=120)
    return d


def adicionar_meses(d: date, meses: int) -> date:
    ano = d.year + (d.month - 1 + meses) // 12
    mes = (d.month - 1 + meses) % 12 + 1
    return date(ano, mes, min(d.day, 28))


def situacao_por_data(fim: Optional[date]) -> str:
    return "concluida" if fim is not None and fim < HOJE else "em_andamento"


# ======================================================================
# Simulação do estado esperado do banco
# ======================================================================
class Mundo:
    """Estado esperado do banco, construído na mesma ordem da carga."""

    def __init__(self):
        self.pessoas: Dict[int, dict] = {}
        self.por_email: Dict[str, int] = {}
        self.por_chave: Dict[str, int] = {}
        self.orgs: List[dict] = [{"nome": "Instituto Federal do Espírito Santo", "sigla": "IFES",
                                  "tipo": "instituicao_ensino"}]
        self.unidades: List[str] = []
        self.grupos: List[dict] = []
        self.areas: Dict[str, str] = {}
        self.inits: Dict[int, dict] = {}
        self.bolsas: Dict[Tuple[str, str], dict] = {}
        self.producoes: List[dict] = []
        self.tipos_formacao: Dict[str, str] = {}
        self.pendencias: List[dict] = []
        self.revisoes: List[dict] = []
        self.contagens: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.perfis: Dict[int, dict] = {}
        self.premios: Dict[int, set] = defaultdict(set)
        self.proficiencias: Dict[int, dict] = defaultdict(dict)
        self.vinculos: Dict[int, set] = defaultdict(set)
        self.formacoes: Dict[int, list] = defaultdict(list)
        self.areas_pessoa: set = set()
        self.alertas_negocio: List[dict] = []
        self._seq_init = 0

    # ----------------------------------------------------------- pessoas
    def ref(self, pid: Optional[int]) -> Optional[str]:
        return None if pid is None else self.pessoas[pid]["ref"]

    def pessoa(self, nome: Optional[str], email: Optional[str] = None) -> Optional[int]:
        nome = (nome or "").strip()
        email = (email or "").strip() or None
        if not nome and not email:
            return None
        if email and email.lower() in self.por_email:
            pid = self.por_email[email.lower()]
            self.pessoas[pid]["emails_fonte"].add(email.lower())
            return pid
        if not nome:
            return None  # negócio: não se cria pessoa sem nome
        chave = chave_pessoa(nome)
        if chave in self.por_chave:
            pid = self.por_chave[chave]
            if email:
                self.por_email[email.lower()] = pid
                self.pessoas[pid]["emails_fonte"].add(email.lower())
            return pid
        return self._criar(nome, email, registrar_chave=True)

    def _criar(self, nome, email, registrar_chave=True, ref=None) -> int:
        pid = len(self.pessoas) + 1
        self.pessoas[pid] = {
            "nome": nome, "ref": ref or nome, "lattes": None,
            "emails_db": {email.lower()} if email else set(),
            "emails_fonte": {email.lower()} if email else set(),
        }
        if registrar_chave:
            self.por_chave[chave_pessoa(nome)] = pid
        if email:
            self.por_email[email.lower()] = pid
        return pid

    # ----------------------------------------------------------- organizações
    def org(self, nome: str, tipo: str) -> str:
        alvo = normalizar_texto(nome)
        for o in self.orgs:
            if normalizar_texto(o["nome"]) == alvo:
                return o["nome"]
        self.orgs.append({"nome": nome, "sigla": None, "tipo": tipo})
        return nome

    def unidade(self, nome: str) -> str:
        alvo = normalizar_texto(nome)
        for u in self.unidades:
            if normalizar_texto(u) == alvo:
                return u
        self.unidades.append(nome)
        return nome

    @staticmethod
    def tipo_org_por_nome(nome: str) -> str:
        texto = f" {normalizar_texto(nome)} "
        if any(f" {t} " in texto for t in ("universidade", "instituto", "faculdade", "escola", "centro federal")):
            return "instituicao_ensino"
        if any(f" {t} " in texto for t in ("prefeitura", "secretaria", "ministerio", "governo")):
            return "orgao_publico"
        return "empresa"

    # ----------------------------------------------------------- grupos / áreas
    def grupo_por_nome(self, nome: Optional[str]) -> Optional[dict]:
        alvo = normalizar_texto(nome)
        if not alvo:
            return None
        for g in self.grupos:
            if normalizar_texto(g["nome"]) == alvo:
                return g
        return None

    def novo_grupo(self, nome, unidade, sigla=None, descricao=None) -> dict:
        g = {"nome": nome, "sigla": sigla, "descricao": descricao, "unidade": unidade,
             "url": None, "data_inicio": None, "membros": {}, "areas": set()}
        self.grupos.append(g)
        return g

    @staticmethod
    def membro(g: dict, pid: int, papel: str, ini=None, fim=None) -> bool:
        if (pid, papel) in g["membros"]:
            return False
        g["membros"][(pid, papel)] = [ini, fim]
        return True

    def area(self, nome: str) -> str:
        alvo = normalizar_texto(nome)
        if alvo not in self.areas:
            self.areas[alvo] = nome.strip()
        return self.areas[alvo]

    # ----------------------------------------------------------- iniciativas
    def nova_init(self, nome, tipo, org, situacao, descricao=None, ini=None, fim=None) -> int:
        self._seq_init += 1
        self.inits[self._seq_init] = {
            "nome": nome, "tipo": tipo, "org": org, "situacao": situacao,
            "descricao": descricao, "ini": ini, "fim": fim, "parts": {}, "areas": set(),
            "equipes": {}, "orgs": set(), "pai": None, "bolsas_part": {},
        }
        return self._seq_init

    def inits_por_nome(self, nome, tipo=None) -> List[int]:
        return [i for i, v in sorted(self.inits.items())
                if v["nome"] == nome and (tipo is None or v["tipo"] == tipo)]

    def participante(self, iid: int, pid: Optional[int], papel: str, ini) -> Optional[Tuple[int, str]]:
        if pid is None:
            return None
        chave = (pid, papel)
        if chave not in self.inits[iid]["parts"]:
            self.inits[iid]["parts"][chave] = ini
        return chave

    def pular(self, passo, motivo, registro, regra="documentada"):
        self.pendencias.append({"passo": passo, "motivo": motivo, "registro": registro, "regra": regra})

    def revisar(self, passo, motivo, registro):
        self.revisoes.append({"passo": passo, "motivo": motivo, "registro": registro})

    def contar(self, passo, evento, n=1):
        self.contagens[passo][evento] += n


# ======================================================================
# Gerador
# ======================================================================
class Gerador:
    def __init__(self, semente: int):
        self.r = random.Random(semente)
        self._tokens_usados = set()
        self._titulos_usados = set()
        self._emails = set()
        self._ids_lattes = set()
        self.registros: List[dict] = []  # catálogo dos 300 registros

    # ----------------------------------------------------------- nomes
    def nome(self) -> str:
        while True:
            primeiro = self.r.choice(PRIMEIROS)
            s1, s2 = self.r.sample(SOBRENOMES, 2)
            nome = f"{primeiro} {s1} {s2}"
            tokens = tuple(sorted(chave_pessoa(nome).split()))
            if tokens not in self._tokens_usados:
                self._tokens_usados.add(tokens)
                return nome

    def email(self, nome: str, dominio: str) -> str:
        partes = slug(nome.split()[0]), slug(nome.split()[-1])
        base = f"{partes[0]}.{partes[1]}"
        email, n = f"{base}@{dominio}", 1
        while email in self._emails:
            n += 1
            email = f"{base}{n}@{dominio}"
        self._emails.add(email)
        return email

    def titulo(self, acoes=ACOES) -> str:
        while True:
            t = f"{self.r.choice(acoes)} {self.r.choice(OBJETOS)} {self.r.choice(COMPLEMENTOS)}"
            if t not in self._titulos_usados:
                self._titulos_usados.add(t)
                return t

    def id_lattes(self) -> str:
        while True:
            valor = "9" + "".join(self.r.choice("0123456789") for _ in range(15))
            if valor not in self._ids_lattes:
                self._ids_lattes.add(valor)
                return valor

    def data(self, ano_ini: int, ano_fim: int) -> date:
        inicio = date(ano_ini, 1, 1)
        dias = (date(ano_fim, 12, 31) - inicio).days
        return inicio + timedelta(days=self.r.randint(0, dias))

    def catalogar(self, rid, fonte, arquivo, tipo, cenario):
        self.registros.append({"id": rid, "fonte": fonte, "arquivo": arquivo,
                               "tipo_caso": tipo, "cenario": cenario})


def gerar(saida: str, semente: int) -> None:
    gen = Gerador(semente)
    r = gen.r
    mundo = Mundo()

    if os.path.exists(saida):
        shutil.rmtree(saida)
    pasta_sigpesq = os.path.join(saida, "sigpesq")
    pasta_lattes = os.path.join(saida, "lattes_json")
    pasta_cnpq = os.path.join(saida, "cnpq_espelhos")
    pasta_pj = os.path.join(saida, "pj")
    for p in ("research_group", "research_projects", "advisorships/2024",
              "advisorships/2025", "advisorships/2026"):
        os.makedirs(os.path.join(pasta_sigpesq, p))
    os.makedirs(pasta_lattes)
    os.makedirs(pasta_cnpq)
    os.makedirs(pasta_pj)

    # ------------------------------------------------------------ pessoas-base
    pesquisadores = []
    for _ in range(80):
        n = gen.nome()
        pesquisadores.append({"nome": n, "email": gen.email(n, "ifes.mock")})
    estudantes = []
    for _ in range(190):
        n = gen.nome()
        estudantes.append({"nome": n, "email": gen.email(n, "aluno.ifes.mock")})
    email_de = {p["nome"]: p["email"] for p in pesquisadores + estudantes}

    # ================================================================ GRUPOS
    grupos_def = []
    temas = r.sample(TEMAS_GRUPO, 23)
    livres = list(pesquisadores)
    r.shuffle(livres)
    for i, tema in enumerate(temas, start=1):
        lideres = [livres.pop() for _ in range(r.choice([1, 1, 2]))]
        equipe = lideres + [livres.pop() for _ in range(r.choice([1, 2]))]
        alunos = r.sample(estudantes, 6)
        nome = f"Grupo de Pesquisa em {tema}"
        grupos_def.append({
            "id": f"G{i:02d}", "tipo": "valido", "cenario": "grupo completo",
            "Nome": nome, "Sigla": "".join(w[0] for w in tema.split() if w[0].isupper()) or tema[:3].upper(),
            "Unidade": r.choice(CAMPI[:3] * 3 + CAMPI), "AreaConhecimento": r.choice(AREAS),
            "Column1": f"http://dgp.cnpq.br/dgp/espelhogrupo/{900000 + i}",
            "lideres": lideres, "equipe": equipe, "alunos": alunos,
            "formato_lideres": r.choice(["; ", ", "]),
        })
    g01, g02 = grupos_def[0], grupos_def[1]
    # exceções
    lider_novo = livres.pop()
    lider_sem_email = livres.pop()
    excecoes_grupo = [
        {"id": "G24", "tipo": "excecao", "cenario": "grupo sem nome (Nome vazio)", "Nome": None,
         "Sigla": "SN", "Unidade": "Serra", "AreaConhecimento": "Física",
         "Column1": None, "lideres": [livres.pop()], "equipe": [], "alunos": []},
        {"id": "G25", "tipo": "excecao", "cenario": "grupo sem unidade (vai para Campus Desconhecido)",
         "Nome": "Grupo de Pesquisa em Oceanografia Costeira", "Sigla": "GPOC", "Unidade": None,
         "AreaConhecimento": "Ciências Biológicas", "Column1": "http://dgp.cnpq.br/dgp/espelhogrupo/900101",
         "lideres": [livres.pop()], "equipe": [], "alunos": r.sample(estudantes, 3)},
        {"id": "G26", "tipo": "excecao", "cenario": "URL do CNPq duplicada (já é do G01)",
         "Nome": "Grupo de Pesquisa em Arte e Tecnologia", "Sigla": "GPAT", "Unidade": "Vitória",
         "AreaConhecimento": "Letras", "Column1": g01["Column1"], "lideres": [livres.pop()],
         "equipe": [], "alunos": []},
        {"id": "G27", "tipo": "excecao", "cenario": "grupo repetido (mesmo nome do G02 em caixa alta e sem acento, URL nova)",
         "Nome": normalizar_texto(g02["Nome"]).upper(), "Sigla": "DUP", "Unidade": "Linhares",
         "AreaConhecimento": "Química", "Column1": "http://dgp.cnpq.br/dgp/espelhogrupo/900102",
         "lideres": [lider_novo], "equipe": [], "alunos": []},
        {"id": "G28", "tipo": "excecao", "cenario": "líderes sem e-mail e líder só com e-mail (sem nome)",
         "Nome": "Grupo de Pesquisa em Patrimônio Histórico", "Sigla": "GPPH", "Unidade": "Santa Teresa",
         "AreaConhecimento": "Educação", "Column1": "http://dgp.cnpq.br/dgp/espelhogrupo/900103",
         "lideres": [lider_sem_email], "equipe": [], "alunos": r.sample(estudantes, 2),
         "Lideres_bruto": f"{lider_sem_email['nome']}; (lider.semnome@ifes.mock)"},
    ]
    linhas_grupo = list(grupos_def)
    for pos, exc in zip([5, 10, 15, 20, 26], excecoes_grupo):
        linhas_grupo.insert(pos, exc)

    planilha = []
    for g in linhas_grupo:
        if "Lideres_bruto" in g:
            lideres_txt = g["Lideres_bruto"]
        else:
            lideres_txt = g.get("formato_lideres", "; ").join(
                f"{l['nome']} ({l['email']})" for l in g["lideres"])
        g["Lideres"] = lideres_txt
        planilha.append({k: g.get(k) for k in ("Nome", "Sigla", "Unidade", "AreaConhecimento", "Column1", "Lideres")})
    pd.DataFrame(planilha).to_excel(
        os.path.join(pasta_sigpesq, "research_group", "Relatorio_mock_grupos.xlsx"), index=False)
    for g in linhas_grupo:
        gen.catalogar(g["id"], "sigpesq_grupos", "sigpesq/research_group/Relatorio_mock_grupos.xlsx",
                      g["tipo"], g["cenario"])

    # --- simulação: grupos
    passo = "grupos_sigpesq"
    for numero, g in enumerate(linhas_grupo, start=1):
        g["linha"] = numero
        nome = (g["Nome"] or "").strip() or None
        if not nome:
            mundo.pular(passo, "grupo sem nome", f"linha {numero}")
            g["esperado"] = {"carregado": False}
            continue
        existente = mundo.grupo_por_nome(nome)
        if existente is not None:
            if g["Column1"] and not any(x is not existente and x["url"] == g["Column1"] for x in mundo.grupos):
                existente["url"] = g["Column1"]
            mundo.contar(passo, "grupos_repetidos")
            g["obj"] = existente
            g["esperado"] = {"carregado": False, "repetido": True}
            continue
        unidade = mundo.unidade(g["Unidade"] or "Campus Desconhecido")
        obj = mundo.novo_grupo(nome, unidade, sigla=g["Sigla"])
        g["obj"] = obj
        if g["Column1"]:
            if any(x is not obj and x["url"] == g["Column1"] for x in mundo.grupos):
                mundo.pular(passo, "URL CNPq não gravada: já é de outro grupo", nome)
            else:
                obj["url"] = g["Column1"]
        if g["AreaConhecimento"]:
            obj["areas"].add(mundo.area(g["AreaConhecimento"]))
        if "Lideres_bruto" in g:
            pid = mundo.pessoa(lider_sem_email["nome"])
            mundo.membro(obj, pid, "lider")
            mundo.contar(passo, "lideres")
            # "(lider.semnome@ifes.mock)": negócio = não criar pessoa sem nome
            mundo.pular(passo, "líder sem nome", nome, regra="negocio")
        else:
            for l in g["lideres"]:
                pid = mundo.pessoa(l["nome"], l["email"])
                if mundo.membro(obj, pid, "lider"):
                    mundo.contar(passo, "lideres")
        mundo.contar(passo, "grupos_criados")
        g["esperado"] = {"carregado": True}

    grupos_validos = [g for g in grupos_def]  # G01..G23 (todos criados)

    # ================================================================ PROJETOS
    def pick_equipe(g, k):
        candidatos = [p for p in g["equipe"] if p not in g["lideres"]] + [x for x in pesquisadores if x not in g["equipe"]][:0]
        return r.sample(candidatos, min(k, len(candidatos)))

    projetos_def = []
    codigo = 6000
    for i in range(1, 62):
        g = r.choice(grupos_validos)
        codigo += 1
        ini = gen.data(2019, 2026)
        if ini > HOJE - timedelta(days=30):
            ini = HOJE - timedelta(days=r.randint(200, 900))
        fim = evitar_hoje(adicionar_meses(ini, r.choice([12, 24, 36])) - timedelta(days=1))
        coord = r.choice(g["lideres"])
        pesq = pick_equipe(g, r.choice([0, 1, 2]))
        alun = r.sample(g["alunos"], r.choice([0, 1, 2, 3]))
        parecer = "Aprovado" if r.random() > 0.12 else "Aprovado com ressalvas"
        kw = r.sample(PALAVRAS, r.choice([0, 1, 2, 3]))
        cod_fmt = r.choice(["PJ {}", "PJ {}", "{}", "PJ-{}"]).format(codigo)
        datas_como_celula = r.random() < 0.15
        projetos_def.append({
            "id": f"P{i:02d}", "tipo": "valido", "cenario": "projeto aprovado completo",
            "Id": cod_fmt, "codigo": str(codigo), "Titulo": gen.titulo(), "ParecerDiretoria": parecer,
            "Inicio": datetime.combine(ini, datetime.min.time()) if datas_como_celula else data_br(ini),
            "Fim": datetime.combine(fim, datetime.min.time()) if datas_como_celula else data_br(fim),
            "ini": ini, "fim": fim,
            "Resumo": f"Resumo fictício do projeto {codigo} gerado para testes do ETL.",
            "Valor Aprovado": r.choice(["", "", "15000,00", "8500"]),
            "Coordenador": coord["nome"], "Pesquisadores": "; ".join(p["nome"] for p in pesq),
            "Estudantes": "; ".join(a["nome"] for a in alun),
            "GrupoPesquisa": g["Nome"] if r.random() > 0.2 else g["Nome"].upper(),
            "ParceiroDemandante": r.choice(PARCEIROS) if r.random() < 0.3 else "",
            "GrupoPesquisaExterno": "Grupo Externo Mock" if r.random() < 0.1 else "",
            "AreaConhecimento": r.choice(AREAS),
            "PalavraChave": r.choice(["; ", ", "]).join(kw),
            "CampusExecucao": g["Unidade"], "grupo": g,
        })
    P = {p["id"]: p for p in projetos_def}

    def proj_exc(pid, cenario, base_grupo=None, **campos):
        g = base_grupo or r.choice(grupos_validos)
        ini = HOJE - timedelta(days=r.randint(300, 900))
        fim = evitar_hoje(adicionar_meses(ini, 24) - timedelta(days=1))
        d = {"id": pid, "tipo": "excecao", "cenario": cenario, "Id": f"PJ {campos.pop('cod', '')}",
             "codigo": None, "Titulo": gen.titulo(), "ParecerDiretoria": "Aprovado",
             "Inicio": data_br(ini), "Fim": data_br(fim), "ini": ini, "fim": fim,
             "Resumo": f"Resumo fictício ({cenario}).", "Valor Aprovado": "",
             "Coordenador": g["lideres"][0]["nome"], "Pesquisadores": "", "Estudantes": "",
             "GrupoPesquisa": g["Nome"], "ParceiroDemandante": "", "GrupoPesquisaExterno": "",
             "AreaConhecimento": r.choice(AREAS), "PalavraChave": "", "CampusExecucao": g["Unidade"],
             "grupo": g}
        d.update(campos)
        return d

    novo_tema_pesq = [livres.pop(), livres.pop()]
    alunos_novos = [estudantes.pop(), estudantes.pop()]
    var_pesq = grupos_validos[3]["lideres"][0]["nome"]
    excecoes_proj = [
        proj_exc("P62", "parecer Reprovado (não deve entrar)", cod=6101, ParecerDiretoria="Reprovado"),
        proj_exc("P63", "parecer Em análise (não deve entrar)", cod=6102, ParecerDiretoria="Em análise"),
        proj_exc("P64", "parecer 'Não aprovado' (não deve entrar)", cod=6103, ParecerDiretoria="Não aprovado"),
        proj_exc("P65", "projeto sem título", cod=6104, Titulo=""),
        proj_exc("P66", "título só com espaços", cod=6105, Titulo="    "),
        proj_exc("P67", "data de início inválida (31/02/2024)", cod=6106, Inicio="31/02/2024"),
        proj_exc("P68", "data de fim em formato inválido (2024/13/45)", cod=6107, Fim="2024/13/45"),
        proj_exc("P69", "data de fim anterior à data de início", cod=6108),
        proj_exc("P70", "campus de execução inválido ('ES', até 3 letras)", cod=6109, CampusExecucao="ES"),
        proj_exc("P71", "grupo de pesquisa inexistente (é criado pelo projeto)", cod=6110,
                 GrupoPesquisa="Grupo de Pesquisa em Cultura Maker", CampusExecucao="Colatina",
                 Coordenador=novo_tema_pesq[0]["nome"], Pesquisadores=novo_tema_pesq[1]["nome"],
                 Estudantes=alunos_novos[0]["nome"], PalavraChave="cultura maker; fabricação digital"),
        proj_exc("P72", "grupo inexistente e campus vazio (grupo vai para Reitoria)", cod=6111,
                 GrupoPesquisa="Grupo de Pesquisa em Políticas Educacionais", CampusExecucao="",
                 Estudantes=alunos_novos[1]["nome"]),
        proj_exc("P73", "código repetido (mesmo Id do P05, título e datas novos)", cod=""),
        proj_exc("P74", "projeto sem código (Id vazio)", cod=""),
        proj_exc("P75", "parecer vazio (entra com situação desconhecida)", cod=6112, ParecerDiretoria=""),
        proj_exc("P76", "coordenador vazio", cod=6113, Coordenador=""),
        proj_exc("P77", "título com mais de 255 caracteres e nomes com acento/caixa/espaços diferentes",
                 cod=6114, Titulo=("Investigação longitudinal " * 12).strip() + " sobre impactos de "
                 "tecnologias digitais em contextos educacionais capixabas",
                 Pesquisadores=f"  {chave_pessoa(var_pesq).upper()}  ;  {var_pesq.lower()} "),
    ]
    e = {x["id"]: x for x in excecoes_proj}
    e["P69"]["Fim"] = data_br(e["P69"]["ini"] - timedelta(days=200))
    e["P73"]["Id"] = P["P05"]["Id"]
    e["P73"]["grupo"] = P["P05"]["grupo"]
    e["P73"]["GrupoPesquisa"] = P["P05"]["grupo"]["Nome"]
    e["P73"]["CampusExecucao"] = P["P05"]["grupo"]["Unidade"]
    e["P73"]["Coordenador"] = P["P05"]["Coordenador"]
    e["P74"]["Id"] = ""
    # P64 só com pessoas, grupo e área que já existem (o defeito não se propaga)
    for x in ("P62", "P63", "P64"):
        e[x]["PalavraChave"] = ""
    linhas_proj = list(projetos_def)
    posicoes = [3, 8, 12, 17, 22, 27, 31, 36, 41, 45, 50, 66, 70, 55, 60, 74]
    for pos, exc in zip(posicoes, excecoes_proj):
        linhas_proj.insert(pos, exc)
    # P73 precisa vir depois do P05
    assert linhas_proj.index(e["P73"]) > linhas_proj.index(P["P05"])

    colunas_proj = ["Id", "Titulo", "ParecerDiretoria", "Inicio", "Fim", "Resumo", "Valor Aprovado",
                    "Coordenador", "Pesquisadores", "Estudantes", "GrupoPesquisa", "ParceiroDemandante",
                    "GrupoPesquisaExterno", "AreaConhecimento", "PalavraChave", "CampusExecucao"]
    pd.DataFrame([{c: p[c] for c in colunas_proj} for p in linhas_proj]).to_excel(
        os.path.join(pasta_sigpesq, "research_projects", "Relatorio_mock_projetos.xlsx"), index=False)
    for p in linhas_proj:
        gen.catalogar(p["id"], "sigpesq_projetos", "sigpesq/research_projects/Relatorio_mock_projetos.xlsx",
                      p["tipo"], p["cenario"])

    # --- simulação: projetos
    passo = "projetos_sigpesq"
    sig_ident: Dict[str, int] = {}
    ifes = "Instituto Federal do Espírito Santo"

    def parse_data(valor) -> Optional[date]:
        if isinstance(valor, datetime):
            return valor.date()
        texto = str(valor or "").strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(texto, fmt).date()
            except ValueError:
                continue
        return None

    def org_campus(campus) -> str:
        c = (campus or "").strip()
        return mundo.unidade(c) if len(c) > 3 else ifes

    def nomes(valor) -> List[str]:
        return [n.strip() for n in str(valor or "").split(";") if n.strip()]

    for numero, p in enumerate(linhas_proj, start=1):
        p["linha"] = numero
        parecer = p["ParecerDiretoria"]
        aprovado = ("aprovado" in parecer.lower()) if parecer.strip() else True
        if parecer.strip().lower() in ("não aprovado", "nao aprovado"):
            aprovado = False  # negócio: "Não aprovado" é reprovação
        if not aprovado:
            mundo.contar(passo, "nao_aprovados")
            p["esperado"] = {"carregado": False, "regra": "negocio" if p["id"] == "P64" else "documentada"}
            continue
        titulo = (p["Titulo"] or "").strip()
        if not titulo:
            mundo.pular(passo, "projeto sem título", f"linha {numero}")
            p["esperado"] = {"carregado": False}
            continue
        ini, fim = parse_data(p["Inicio"]), parse_data(p["Fim"])
        if parecer == "Aprovado":
            situacao = situacao_por_data(fim)
        elif "aprovado" in parecer.lower():
            situacao = situacao_por_data(fim)
        else:
            situacao = "desconhecida"
        org = org_campus(p["CampusExecucao"])
        codigo = normalizar_texto(__import__("re").search(r"\d+", p["Id"]).group(0)) if __import__("re").search(r"\d+", str(p["Id"])) else ""
        ident = f"sigpesq project|{codigo}" if codigo else f"sem-codigo|{numero}"
        campos = {"nome": titulo, "situacao": situacao, "descricao": p["Resumo"] or None,
                  "ini": ini, "fim": fim, "org": org}
        if ident in sig_ident:
            iid = sig_ident[ident]
            mundo.inits[iid].update(campos)
            mundo.contar(passo, "projeto_pesquisa_atualizadas")
        else:
            iid = mundo.nova_init(titulo, "projeto_pesquisa", org, situacao, campos["descricao"], ini, fim)
            mundo.contar(passo, "projeto_pesquisa_criadas")
            sig_ident[ident] = iid
        p["iid"] = iid
        p["codigo_norm"] = codigo
        coord = p["Coordenador"].strip()
        mundo.participante(iid, mundo.pessoa(coord) if coord else None, "coordenador", ini)
        for n in nomes(p["Pesquisadores"]):
            mundo.participante(iid, mundo.pessoa(n), "pesquisador", ini)
        for n in nomes(p["Estudantes"]):
            mundo.participante(iid, mundo.pessoa(n), "estudante", ini)
        nome_grupo = (p["GrupoPesquisa"] or "").strip()
        grupo = mundo.grupo_por_nome(nome_grupo) if nome_grupo else None
        if nome_grupo and grupo is None:
            campus = (p["CampusExecucao"] or "").strip() or "Reitoria"
            grupo = mundo.novo_grupo(nome_grupo, mundo.unidade(campus),
                                     descricao=f"Grupo de Pesquisa importado do SigPesq: {nome_grupo}")
            membros_p = ([coord] if coord else []) + nomes(p["Pesquisadores"])
            for n in membros_p:
                mundo.membro(grupo, mundo.pessoa(n), "pesquisador", ini)
            for n in nomes(p["Estudantes"]):
                mundo.membro(grupo, mundo.pessoa(n), "estudante", ini)
            mundo.contar(passo, "grupos_criados_pelo_projeto")
            p["grupo_criado"] = grupo
        if grupo is not None:
            mundo.inits[iid]["equipes"][id(grupo)] = (grupo, "executor")
        if p["AreaConhecimento"]:
            mundo.inits[iid]["areas"].add(mundo.area(p["AreaConhecimento"]))
        kw = (p["PalavraChave"] or "").strip()
        if kw:
            sep = ";" if ";" in kw else ","
            areas_kw = [mundo.area(t.strip()) for t in kw.split(sep) if t.strip()]
            pessoas_kw = [mundo.pessoa(n) for n in ([coord] if coord else []) + nomes(p["Pesquisadores"])]
            for a in areas_kw:
                mundo.inits[iid]["areas"].add(a)
                if grupo is not None:
                    grupo["areas"].add(a)
                for pid in pessoas_kw:
                    mundo.areas_pessoa.add((pid, a))
        if p["ParceiroDemandante"]:
            o = mundo.org(p["ParceiroDemandante"], mundo.tipo_org_por_nome(p["ParceiroDemandante"]))
            mundo.inits[iid]["orgs"].add((o, "demandante"))
        if str(p["Valor Aprovado"]).strip():
            mundo.contar(passo, "descartado:valor_aprovado")
        if str(p["GrupoPesquisaExterno"]).strip():
            mundo.contar(passo, "descartado:grupo_pesquisa_externo")
        p["esperado"] = {"carregado": True}

    projetos_carregados = [p for p in linhas_proj if p.get("iid") and p["tipo"] == "valido"]

    # ================================================================ BOLSISTAS
    bolsistas_def = []
    alunos_usados = []
    titulo_pt_repetido = None
    rid = 10000
    validos_pais = [p for p in projetos_carregados if p["id"] != "P05"]
    for i in range(1, 97):
        pai = r.choice(validos_pais)
        rid += 1
        aluno = estudantes.pop() if r.random() < 0.75 or not alunos_usados else r.choice(alunos_usados)
        alunos_usados.append(aluno)
        orientador_nome = r.choice([pai["Coordenador"]] + nomes(pai["Pesquisadores"]))
        orientador_email = email_de[orientador_nome]
        programa, agencia, valor_txt, valor = r.choice(FINANCIAMENTOS)
        ini_pai, fim_pai = pai["ini"], pai["fim"]
        ini = ini_pai + timedelta(days=r.randint(0, max(1, (fim_pai - ini_pai).days // 2)))
        fim = evitar_hoje(min(fim_pai, ini + timedelta(days=364)))
        cenario = "plano de trabalho com bolsa"
        if i in (11, 22, 33):
            fim = evitar_hoje(fim_pai + timedelta(days=r.randint(60, 200)))
            cenario = "plano que termina depois do projeto (estende o fim do projeto pai)"
        if i in (44, 55):
            ini = ini_pai - timedelta(days=r.randint(30, 120))
            cenario = "plano que começa antes do projeto (antecipa o início do pai)"
        titulo_pt = gen.titulo(ACOES_PT)
        if i in (5, 15, 25, 35, 45):
            titulo_pt = pai["Titulo"]
            cenario = "título do plano igual ao do projeto (recebe sufixo | Orientacao)"
        bolsistas_def.append({
            "id": f"B{i:03d}", "tipo": "valido", "cenario": cenario,
            "Id": rid, "Orientado": aluno["nome"], "OrientadoEmail": aluno["email"],
            "Orientador": orientador_nome, "OrientadorEmail": orientador_email,
            "TituloPT": titulo_pt, "CodPT": f"PT {20000 + i}", "CodPJ": pai["Id"], "TituloPJ": pai["Titulo"],
            "Inicio": data_br(ini), "Fim": data_br(fim),
            "Programa": programa.lower() if r.random() < 0.15 else programa, "Valor": valor_txt,
            "AgFinanciadora": agencia, "CampusExecucao": pai["CampusExecucao"], "Cancelado": r.choice(["", "", "Não", 0]),
            "valor_esperado": valor, "pai": pai, "aluno": aluno,
        })
    B = {b["id"]: b for b in bolsistas_def}
    if titulo_pt_repetido is None:
        titulo_pt_repetido = B["B007"]["TituloPT"]

    def bols_exc(bid, cenario, **campos):
        pai = r.choice(validos_pais)
        nonlocal_rid[0] += 1
        aluno = estudantes.pop()
        ini = pai["ini"] + timedelta(days=30)
        fim = evitar_hoje(min(pai["fim"], ini + timedelta(days=364)))
        d = {"id": bid, "tipo": "excecao", "cenario": cenario, "Id": nonlocal_rid[0],
             "Orientado": aluno["nome"], "OrientadoEmail": aluno["email"],
             "Orientador": pai["Coordenador"], "OrientadorEmail": email_de[pai["Coordenador"]],
             "TituloPT": gen.titulo(ACOES_PT), "CodPT": f"PT {21000 + int(bid[1:])}", "CodPJ": pai["Id"],
             "TituloPJ": pai["Titulo"], "Inicio": data_br(ini), "Fim": data_br(fim), "Programa": "PIBIC",
             "Valor": "700,00", "AgFinanciadora": "CNPq", "CampusExecucao": pai["CampusExecucao"],
             "Cancelado": "", "valor_esperado": 700.0, "pai": pai, "aluno": aluno}
        d.update(campos)
        return d

    nonlocal_rid = [rid]
    aluno_com_email = B["B003"]["aluno"]
    aluno_variacao = B["B009"]["aluno"]
    excecoes_bols = [
        bols_exc("B097", "orientado sem nome e sem e-mail", Orientado="", OrientadoEmail=""),
        bols_exc("B098", "orientado sem nome e sem e-mail (só espaços)", Orientado="   ", OrientadoEmail=" "),
        bols_exc("B099", "orientado sem nome e sem e-mail, sem programa", Orientado="", OrientadoEmail="", Programa=""),
        bols_exc("B100", "orientado sem nome, e-mail de aluno já cadastrado", Orientado="",
                 OrientadoEmail=aluno_com_email["email"]),
        bols_exc("B101", "orientado sem nome, e-mail novo", Orientado="",
                 OrientadoEmail="aluno.sem.nome@aluno.ifes.mock"),
        bols_exc("B102", "plano sem título (TituloPT vazio)", TituloPT=""),
        bols_exc("B103", "plano sem título (TituloPT só espaços)", TituloPT="   "),
        bols_exc("B104", "bolsa cancelada (Cancelado=Sim)", Cancelado="Sim"),
        bols_exc("B105", "bolsa cancelada (Cancelado=1)", Cancelado=1),
        bols_exc("B106", "bolsa sem agência financiadora", AgFinanciadora=""),
        bols_exc("B107", "bolsa sem agência financiadora (PIBITI)", AgFinanciadora="", Programa="PIBITI"),
        bols_exc("B108", "valor com separador de milhar (1.200,00)", Programa="PIBITI",
                 AgFinanciadora="Petrobras Mock", Valor="1.200,00", valor_esperado=1200.0),
        bols_exc("B109", "valor com símbolo de moeda (R$ 750,00)", Programa="PIBIC",
                 AgFinanciadora="Vale Mock", Valor="R$ 750,00", valor_esperado=750.0),
        bols_exc("B110", "valor diferente para a mesma bolsa PIBIC/CNPq (850,00)", Valor="850,00",
                 valor_esperado=700.0),
        bols_exc("B111", "valor não numérico ('a definir')", Programa="PIBIC-AF", AgFinanciadora="CNPq",
                 Valor="a definir", valor_esperado=None),
        bols_exc("B112", "projeto pai inexistente (CodPJ 7999)", CodPJ="PJ 7999",
                 TituloPJ="Projeto provisório mock de monitoramento ambiental"),
        bols_exc("B113", "segundo plano do mesmo projeto pai inexistente (CodPJ 7999)", CodPJ="PJ 7999",
                 TituloPJ="Projeto provisório mock de monitoramento ambiental"),
        bols_exc("B114", "sem projeto pai (CodPJ e TituloPJ vazios)", CodPJ="", TituloPJ=""),
        bols_exc("B115", "datas em formato inválido (2025-13-01 / abc)", Inicio="2025-13-01", Fim="abc"),
        bols_exc("B116", "data de início inexistente (31/02/2025)", Inicio="31/02/2025"),
        bols_exc("B117", "mesmo aluno com e-mail em maiúsculas", Orientado=aluno_com_email["nome"],
                 OrientadoEmail=aluno_com_email["email"].upper()),
        bols_exc("B118", "mesmo aluno (mesmo e-mail) com nome escrito diferente",
                 Orientado=chave_pessoa(aluno_variacao["nome"]).title() + " Jr",
                 OrientadoEmail=aluno_variacao["email"]),
        bols_exc("B119", "linha repetida do B020 (mesmo CodPT, fim alterado)"),
        bols_exc("B120", "título do plano igual ao de outro plano (B007), código diferente",
                 TituloPT=titulo_pt_repetido),
    ]
    eb = {x["id"]: x for x in excecoes_bols}
    for x in ("B112", "B113"):
        eb[x]["pai"] = None
    eb["B114"]["pai"] = None
    eb["B110"]["Programa"], eb["B110"]["AgFinanciadora"] = "PIBIC", "CNPq"
    base = B["B020"]
    eb["B119"].update({k: base[k] for k in ("Id", "Orientado", "OrientadoEmail", "Orientador", "OrientadorEmail",
                                             "TituloPT", "CodPT", "CodPJ", "TituloPJ", "Inicio", "Programa",
                                             "Valor", "AgFinanciadora", "CampusExecucao", "pai", "valor_esperado")})
    eb["B119"]["aluno"] = base["aluno"]
    eb["B119"]["Fim"] = data_br(evitar_hoje(datetime.strptime(base["Fim"], "%d/%m/%Y").date() + timedelta(days=90)))
    for x in ("B117", "B118", "B100"):
        eb[x]["aluno"] = None
    linhas_bols = list(bolsistas_def)
    posicoes = [4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 84, 89, 94, 99, 104, 109, 114, 119]
    for pos, exc in zip(posicoes, excecoes_bols):
        linhas_bols.insert(pos, exc)
    assert linhas_bols.index(eb["B119"]) > linhas_bols.index(B["B020"])
    assert linhas_bols.index(eb["B120"]) > linhas_bols.index(B["B007"])
    assert linhas_bols.index(eb["B100"]) > linhas_bols.index(B["B003"])

    colunas_b = ["Id", "Orientado", "OrientadoEmail", "Orientador", "OrientadorEmail", "TituloPT", "CodPT",
                 "CodPJ", "TituloPJ", "Inicio", "Fim", "Programa", "Valor", "AgFinanciadora",
                 "CampusExecucao", "Cancelado"]
    arquivos_b = []
    for k, ano in enumerate(("2024", "2025", "2026")):
        fatia = linhas_bols[k * 40:(k + 1) * 40]
        caminho = os.path.join(pasta_sigpesq, "advisorships", ano, f"Relatorio_mock_bolsistas_{ano}.xlsx")
        pd.DataFrame([{c: b[c] for c in colunas_b} for b in fatia]).to_excel(caminho, index=False)
        arquivos_b.append(caminho)
        for b in fatia:
            gen.catalogar(b["id"], "sigpesq_bolsistas", os.path.relpath(caminho, saida), b["tipo"], b["cenario"])
    # ordem de leitura do ETL = ordem de modificação dos arquivos
    agora = time.time()
    for k, caminho in enumerate(arquivos_b):
        os.utime(caminho, (agora - 300 + k * 60, agora - 300 + k * 60))

    # --- simulação: bolsistas
    passo = "bolsistas_sigpesq"
    import re as _re

    def parse_valor(txt) -> Optional[float]:
        """Negócio: valor em reais, com ou sem R$ e separador de milhar."""
        t = str(txt or "").replace("R$", "").strip()
        if not t:
            return 0.0
        t = t.replace(".", "").replace(",", ".") if "," in t else t
        try:
            return float(t)
        except ValueError:
            return None

    for numero, b in enumerate(linhas_bols, start=1):
        b["linha"] = numero
        nome_aluno = str(b["Orientado"]).strip()
        email_aluno = str(b["OrientadoEmail"]).strip()
        titulo = str(b["TituloPT"]).strip()
        if (not nome_aluno and not email_aluno) or not titulo:
            mundo.pular(passo, "bolsista sem nome/e-mail ou plano sem título", f"linha {numero}")
            b["esperado"] = {"carregado": False}
            continue
        # pai
        pai_iid = None
        titulo_pai = str(b["TituloPJ"]).strip()
        if titulo_pai:
            m = _re.search(r"\d+", str(b["CodPJ"]))
            ident_pai = f"sigpesq project|{m.group(0)}" if m else None
            if ident_pai:
                pai_iid = sig_ident.get(ident_pai)
            else:
                ids = mundo.inits_por_nome(titulo_pai, "projeto_pesquisa")
                pai_iid = ids[0] if ids else None
            if pai_iid is None:
                pai_iid = mundo.nova_init(titulo_pai, "projeto_pesquisa", ifes, "desconhecida")
                mundo.contar(passo, "projetos_pai_provisorios")
            if ident_pai:
                sig_ident[ident_pai] = pai_iid
        m = _re.search(r"\d+", str(b["CodPT"]))
        ident = f"sigpesq workplan|{m.group(0)}"
        existente = sig_ident.get(ident)
        ini, fim = parse_data(b["Inicio"]), parse_data(b["Fim"])
        cancel = str(b["Cancelado"]).strip().lower() in ("1", "sim", "s", "true", "t", "yes", "y")
        situacao = "cancelada" if cancel else situacao_por_data(fim)
        em_uso = any(i != existente for i in mundo.inits_por_nome(titulo))
        nome = titulo
        if em_uso:
            partes = []
            if nome_aluno:
                partes.append(nome_aluno)
            if ini:
                partes.append(str(ini.year))
            partes.append(f"sigpesq {b['Id']}")
            nome = f"{titulo} | Orientacao {' | '.join(partes)}"
        org = org_campus(b["CampusExecucao"])
        campos = {"nome": nome, "situacao": situacao, "descricao": f"Programa: {b['Programa'] or 'N/A'}",
                  "ini": ini, "fim": fim, "org": org}
        if existente is None:
            iid = mundo.nova_init(nome, "orientacao", org, situacao, campos["descricao"], ini, fim)
            mundo.contar(passo, "orientacao_criadas")
        else:
            iid = existente
            mundo.inits[iid].update(campos)
            mundo.contar(passo, "orientacao_atualizadas")
        sig_ident[ident] = iid
        b["iid"] = iid
        if pai_iid is not None:
            mundo.inits[iid]["pai"] = pai_iid
        pid_aluno = mundo.pessoa(nome_aluno or None, email_aluno or None)
        if pid_aluno is None and email_aluno:
            mundo.pular(passo, "orientando sem nome", f"linha {numero}", regra="negocio")
        orientando = mundo.participante(iid, pid_aluno, "orientando", ini)
        pid_orientador = mundo.pessoa(b["Orientador"], b["OrientadorEmail"])
        mundo.participante(iid, pid_orientador, "orientador", ini)
        financiadora = str(b["AgFinanciadora"]).strip()
        org_fin = None
        if financiadora:
            org_fin = mundo.org(financiadora, "fomento")
            mundo.inits[iid]["orgs"].add((org_fin, "financiadora"))
        programa = str(b["Programa"]).strip().upper()
        if programa:
            if org_fin is None:
                mundo.pular(passo, "bolsa sem financiador", f"{programa} em {nome}")
            else:
                chave_b = (programa.lower(), org_fin)
                if chave_b not in mundo.bolsas:
                    valor = parse_valor(b["Valor"])
                    mundo.bolsas[chave_b] = {"nome": programa, "financiador": org_fin, "valor": valor,
                                             "linha": b["id"]}
                    if valor is None:
                        mundo.alertas_negocio.append({"registro": b["id"], "alerta": "valor da bolsa não numérico"})
                b["bolsa_chave"] = chave_b
                if orientando is not None:
                    mundo.inits[iid]["bolsas_part"][orientando] = chave_b
        if pai_iid is not None:
            mundo.participante(pai_iid, pid_orientador, "pesquisador", ini)
            mundo.participante(pai_iid, pid_aluno, "estudante", ini)
        if cancel:
            mundo.contar(passo, "descartado:dados_cancelamento")
        b["esperado"] = {"carregado": True}

    # recálculo do pai
    filhos = defaultdict(list)
    for iid, v in mundo.inits.items():
        if v["pai"] is not None:
            filhos[v["pai"]].append(v)
    for pai_iid, lista in filhos.items():
        pai = mundo.inits[pai_iid]
        inis = [f["ini"] for f in lista if f["ini"]]
        fins = [f["fim"] for f in lista if f["fim"]]
        ini, fim = (min(inis) if inis else None), (max(fins) if fins else None)
        mudou = False
        if ini and (pai["ini"] is None or ini < pai["ini"]):
            pai["ini"] = ini
            mudou = True
        if fim and (pai["fim"] is None or fim > pai["fim"]):
            pai["fim"] = fim
            mudou = True
        if pai["fim"] and pai["situacao"] in ("desconhecida", "em_andamento", "concluida"):
            nova = situacao_por_data(pai["fim"])
            if nova != pai["situacao"]:
                pai["situacao"] = nova
                mudou = True
        if mudou:
            mundo.contar(passo, "projetos_pai_recalculados")

    # ================================================================ CNPq
    cnpq_def = []
    grupos_com_url = [g for g in mundo.grupos if g["url"]]
    assert len(grupos_com_url) == 25, len(grupos_com_url)
    r.shuffle(grupos_com_url)
    externos_cnpq = []
    for k, g in enumerate(grupos_com_url, start=1):
        gdef = next(x for x in linhas_grupo if x.get("obj") is g and x["Nome"])
        lideres = [l["nome"] for l in gdef["lideres"]] if "Lideres_bruto" not in gdef else [lider_sem_email["nome"]]
        equipe = [p["nome"] for p in gdef["equipe"] if p["nome"] not in lideres]
        alunos = [a["nome"] for a in gdef["alunos"]][:3]
        esp = {
            "nome_grupo": g["nome"],
            "repercussoes": f"Repercussões fictícias do grupo {g['nome']} (espelho mock).",
            "identificacao": {"ano_de_formacao": str(r.randint(2008, 2022)), "lideres_do_grupo": list(lideres)},
            "recursos_humanos": {
                "pesquisadores": [{"nome": n, "data_inclusao": data_br(gen.data(2015, 2023))} for n in lideres + equipe],
                "estudantes": [{"nome": n, "data_inclusao": data_br(gen.data(2020, 2025)), "nivel": "Graduação"}
                               for n in alunos],
            },
            "linhas_de_pesquisa": {"linhas": [{"nome_da_linha_de_pesquisa": x}
                                              for x in r.sample(PALAVRAS + AREAS, r.choice([1, 2, 3]))]},
        }
        cenario, tipo = "espelho completo", "valido"
        if k <= 20:
            if k in (2, 9, 14):
                esp["nome_grupo"] = g["nome"].replace("Grupo de Pesquisa em", "Núcleo de Estudos em")
                cenario = "espelho com nome oficial diferente (grupo é renomeado)"
            if k in (3, 7, 11, 17):
                novo = gen.nome()
                externos_cnpq.append(novo)
                esp["recursos_humanos"]["tecnicos"] = [{"nome": novo, "data_inclusao": data_br(gen.data(2018, 2024))}]
            if k in (4, 12):
                eg = gen.nome()
                esp["recursos_humanos"]["egressos_estudantes"] = [
                    {"nome": eg, "data_inclusao": "01/03/2019", "data_egresso": "28/02/2021", "nivel": "Mestrado"}]
            if k in (5, 15):
                novo_lider = gen.nome()
                esp["identificacao"]["lideres_do_grupo"].append(novo_lider)
                cenario = "espelho com líder que não está no SigPesq"
        elif k == 21:
            esp = {"__erro__": "timeout simulado ao acessar o espelho"}
            cenario, tipo = "espelho indisponível (erro de rede simulado)", "excecao"
        elif k == 22:
            esp["nome_grupo"] = "CNPq"
            esp["identificacao"] = {"data_de_formacao": "Anterior a março de 2010",
                                    "lideres_do_grupo": list(lideres)}
            cenario, tipo = "nome do grupo 'CNPq' (ignorado) e formação 'Anterior a março de 2010'", "excecao"
        elif k == 23:
            eg = gen.nome()
            esp["recursos_humanos"]["egressos_pesquisadores"] = [{"nome": eg, "data_inclusao": "10/04/2016"}]
            cenario, tipo = "egresso sem data de saída (vai para revisão)", "excecao"
            esp["_egresso_sem_fim"] = eg
        elif k == 24:
            esp["recursos_humanos"]["estudantes"] += [{"nome": "ui-button", "data_inclusao": "01/01/2020"},
                                                      {"nome": "   ", "data_inclusao": "01/01/2020"}]
            novo = gen.nome()
            esp["recursos_humanos"]["pesquisadores"].append({"nome": novo, "data_inclusao": "32/13/2019"})
            eg = gen.nome()
            esp["recursos_humanos"]["egressos"] = [{"nome": eg, "data_inclusao": "05/05/2017",
                                                     "data_egresso": "Não informada", "nivel": "Doutorado"}]
            cenario, tipo = "nomes-placeholder, data inválida e egresso com data 'Não informada'", "excecao"
        elif k == 25:
            alvo = (lideres + equipe)[0]
            esp["recursos_humanos"]["egressos_pesquisadores"] = [
                {"nome": alvo, "data_inclusao": "01/01/2015", "data_egresso": "30/06/2023"}]
            cenario, tipo = "mesma pessoa como pesquisador ativo e egresso (data de fim atualizada)", "excecao"
        cid = f"C{k:02d}"
        arquivo = os.path.join(pasta_cnpq, f"{cid}_{g['url'].rsplit('/', 1)[-1]}.json")
        espelho_publico = {kk: vv for kk, vv in esp.items() if not kk.startswith("_")}
        with open(arquivo, "w", encoding="utf-8") as fh:
            json.dump({"url": g["url"], "espelho": espelho_publico}, fh, ensure_ascii=False, indent=2)
        cnpq_def.append({"id": cid, "tipo": tipo, "cenario": cenario, "grupo": g, "esp": esp, "url": g["url"]})
        gen.catalogar(cid, "cnpq_espelhos", os.path.relpath(arquivo, saida), tipo, cenario)

    # --- simulação: CNPq (ordem = ordem dos grupos no banco)
    passo = "cnpq"
    ordem_grupos = [g for g in mundo.grupos if g["url"]]
    por_url = {c["url"]: c for c in cnpq_def}

    def data_cnpq(valor) -> Optional[date]:
        t = str(valor or "").strip()
        if t.lower() in ("", "não informada", "não informado", "n/a"):
            return None
        try:
            return datetime.strptime(t, "%d/%m/%Y").date()
        except ValueError:
            pass
        meses = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
                 "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
        if "anterior a" in t.lower():
            partes = t.lower().replace("anterior a", "").strip().split(" de ")
            if len(partes) == 2 and partes[1].strip().isdigit():
                return date(int(partes[1]), meses.get(partes[0].strip(), 1), 1)
        return None

    for g in ordem_grupos:
        c = por_url[g["url"]]
        esp = c["esp"]
        c["nome_antes"] = g["nome"]
        if "__erro__" in esp:
            mundo.pular(passo, "falha ao ler o espelho do CNPq", g["nome"])
            continue
        nome = esp.get("nome_grupo")
        if nome and nome.upper() == "CNPQ":
            nome = None
        if nome:
            g["nome"] = nome
        if esp.get("repercussoes"):
            g["descricao"] = esp["repercussoes"]
        ident = esp.get("identificacao") or {}
        valor = ident.get("ano_de_formacao") or ident.get("data_de_formacao")
        formacao = date(int(valor), 1, 1) if valor and len(valor) == 4 and valor.isdigit() else data_cnpq(valor)
        if formacao:
            g["data_inicio"] = formacao
        rh = esp.get("recursos_humanos") or {}
        membros = []
        for item in rh.get("pesquisadores", []):
            membros.append((item["nome"], "pesquisador", False, item.get("data_inclusao"), item.get("data_egresso")))
        for item in rh.get("estudantes", []):
            membros.append((item["nome"], "estudante", False, item.get("data_inclusao"), item.get("data_egresso")))
        for item in rh.get("tecnicos", []):
            membros.append((item["nome"], "tecnico", False, item.get("data_inclusao"), item.get("data_egresso")))
        for chave_rh, papel in (("egressos", None), ("egressos_pesquisadores", "pesquisador"),
                                ("egressos_estudantes", "estudante")):
            for item in rh.get(chave_rh, []):
                pap = papel or ("estudante" if item.get("nivel") or "estudante" in str(item).lower() else "pesquisador")
                membros.append((item["nome"], pap, True, item.get("data_inclusao"), item.get("data_egresso")))
        for l in ident.get("lideres_do_grupo", []):
            membros.append((l, "lider", False, None, None))
        for nome_m, papel, egresso, ini_txt, fim_txt in membros:
            nome_m = (nome_m or "").strip()
            if not nome_m or nome_m.lower() == "ui-button":
                continue
            pid = mundo.pessoa(nome_m)
            ini = data_cnpq(ini_txt)
            fim = data_cnpq(fim_txt) if fim_txt else None
            if mundo.membro(g, pid, papel, ini, fim):
                mundo.contar(passo, "membros")
            elif fim and g["membros"][(pid, papel)][1] != fim:
                g["membros"][(pid, papel)][1] = fim
                mundo.contar(passo, "membros_com_fim_atualizado")
            if egresso and fim is None:
                mundo.revisar(passo, "egresso sem data de fim no CNPq", f"{nome_m} em {g['nome']}")
        for linha in (esp.get("linhas_de_pesquisa") or {}).get("linhas", []):
            g["areas"].add(mundo.area(linha["nome_da_linha_de_pesquisa"]))
        mundo.contar(passo, "grupos_sincronizados")

    # ================================================================ LATTES
    lattes_def = []
    pj_l01 = next(p for p in projetos_carregados if p["id"] != "P05")
    candidatos_donos = [pj_l01["Coordenador"]]
    candidatos_donos += [p["Coordenador"] for p in projetos_carregados]
    candidatos_donos += [n for p in projetos_carregados for n in nomes(p["Pesquisadores"])]
    candidatos_donos += [x["nome"] for g in grupos_def for x in g["equipe"]]
    donos_pool = list(dict.fromkeys(candidatos_donos))[:35]
    assert len(donos_pool) == 35, len(donos_pool)
    # L06 precisa ser orientador de um plano válido do SigPesq
    b06 = next(b for b in linhas_bols if b["tipo"] == "valido" and b.get("iid")
               and b["Orientador"] in donos_pool[1:])
    donos_pool.remove(b06["Orientador"])
    donos_pool.insert(5, b06["Orientador"])
    externos = [gen.nome() for _ in range(5)]

    def citacao(nome: str) -> str:
        partes = nome.split()
        return f"{slug(partes[-1]).upper()}, {partes[0][0]}. {partes[1][0]}."

    def cv_base(nome: str, lattes_id: str) -> dict:
        ano_grad = r.randint(1995, 2010)
        orientador_dout = r.choice(pesquisadores)["nome"] if r.random() < 0.3 else gen.nome()
        tese = f"Contribuições para {r.choice(OBJETOS)} {r.choice(COMPLEMENTOS)}"
        cv = {
            "informacoes_pessoais": {
                "nome_completo": nome, "id_lattes": lattes_id,
                "texto_resumo": f"Currículo fictício de {nome}, gerado para testes do ETL do Horizon.",
                "nome_citacoes": f"{citacao(nome)};{slug(nome.split()[-1]).upper()}, {nome.split()[0].upper()}",
                "atualizacao_cv": data_br(gen.data(2023, 2026) if True else HOJE),
                "url": f"http://lattes.cnpq.br/{lattes_id}",
            },
            "premios_titulos": [{"descricao": f"Menção honrosa fictícia {k} - {nome.split()[0]}",
                                 "ano": str(r.randint(2010, 2025))} for k in range(r.choice([0, 1, 2]))],
            "idiomas": [{"nome": i, "le": r.choice(list(NIVEIS)), "escreve": r.choice(list(NIVEIS)),
                         "fala": r.choice(list(NIVEIS)), "compreende": r.choice(list(NIVEIS))}
                        for i in r.sample(IDIOMAS, r.choice([1, 2]))],
            "atuacao_profissional": [
                {"instituicao": "Instituto Federal do Espírito Santo", "ano_inicio": str(r.randint(2008, 2018)),
                 "ano_fim": "Atual", "vinculo": "Servidor Público", "enquadramento": "Professor EBTT"}],
            "formacao_academica": [
                {"tipo": f"Graduação em {r.choice(AREAS)}", "nome_instituicao": r.choice(INSTITUICOES_ENSINO),
                 "ano_inicio": str(ano_grad), "ano_conclusao": str(ano_grad + 4)},
                {"tipo": f"Doutorado em {r.choice(AREAS)}", "nome_instituicao": r.choice(INSTITUICOES_ENSINO),
                 "ano_inicio": str(ano_grad + 6), "ano_conclusao": str(ano_grad + 10),
                 "descricao": f"Título: {tese}, Ano de Obtenção: {ano_grad + 10}. Orientador: {orientador_dout}."},
            ],
            "producao_bibliografica": {"artigos_periodicos": [], "trabalhos_completos_congressos": []},
            "producao_tecnica": {},
            "projetos_pesquisa": [], "projetos_extensao": [], "projetos_desenvolvimento": [],
            "orientacoes": {"concluidas": {}, "em_andamento": {}},
        }
        if r.random() < 0.4:
            cv["atuacao_profissional"].append(
                {"instituicao": r.choice(EMPRESAS), "ano_inicio": str(r.randint(2003, 2007)),
                 "ano_fim": str(r.randint(2008, 2010)), "vinculo": r.choice(VINCULOS[1:])})
        return cv

    doi_seq = [0]

    def artigo(autores: List[str], **extra) -> dict:
        doi_seq[0] += 1
        d = {"titulo": f"{r.choice(['Uma abordagem', 'Um estudo', 'Avaliação experimental', 'Análise comparativa'])} "
                       f"de {r.choice(OBJETOS)} {r.choice(COMPLEMENTOS)} ({doi_seq[0]})",
             "ano": str(r.randint(2015, 2025)), "revista": r.choice(REVISTAS), "volume": str(r.randint(1, 40)),
             "paginas": f"{r.randint(1, 90)}-{r.randint(91, 200)}", "doi": f"10.5555/mock.{doi_seq[0]:04d}",
             "autores": "; ".join(autores)}
        d.update(extra)
        return d

    def congresso(autores: List[str]) -> dict:
        doi_seq[0] += 1
        return {"titulo": f"Relato de experiência com {r.choice(OBJETOS)} ({doi_seq[0]})",
                "ano": str(r.randint(2016, 2025)), "evento": r.choice(EVENTOS),
                "paginas": f"{r.randint(1, 9)}-{r.randint(10, 20)}", "autores": "; ".join(autores)}

    def projeto_lattes(titulo, ini, fim, integrantes, financiador=None, desc=None) -> dict:
        return {"nome": titulo, "ano_inicio": str(ini), "ano_conclusao": fim,
                "descricao": [f"Descrição: {desc or 'Projeto fictício para teste do ETL'}. "
                              f"Situação: {'Em andamento' if fim == 'Atual' else 'Concluído'}; Natureza: Pesquisa."],
                "integrantes": [{"nome": n, "papel": p} for n, p in integrantes],
                "financiadores": [{"nome": financiador}] if financiador else []}

    donos_nomes = donos_pool + externos
    for k, nome in enumerate(donos_nomes, start=1):
        lid = gen.id_lattes()
        cv = cv_base(nome, lid)
        lattes_def.append({"id": f"L{k:02d}", "tipo": "valido", "cenario": "currículo completo",
                           "nome": nome, "lattes_id": lid, "cv": cv})
    L = {x["id"]: x for x in lattes_def}

    # conteúdo cruzado (artigos com coautores, projetos e orientações)
    for x in lattes_def:
        outros = r.sample([y for y in lattes_def if y is not x], 2)
        autores = [citacao(x["nome"])] + [citacao(o["nome"]) for o in outros[:r.choice([0, 1, 2])]] + ["EXTERNO, F. M."]
        r.shuffle(autores)
        x["cv"]["producao_bibliografica"]["artigos_periodicos"] = [artigo(autores) for _ in range(r.choice([1, 2]))]
        if r.random() < 0.5:
            x["cv"]["producao_bibliografica"]["trabalhos_completos_congressos"] = [congresso([citacao(x["nome"])])]
        if r.random() < 0.3:
            x["cv"]["producao_tecnica"] = {"softwares_sem_patente": [
                {"titulo": f"Software mock {slug(x['nome'])[:10]}", "ano": str(r.randint(2018, 2025))}]}
        ini = r.randint(2016, 2023)
        fim = "Atual" if r.random() < 0.4 else str(r.randint(ini + 1, 2025))
        integrantes = [(x["nome"], "Coordenador")] + [(n, "Integrante") for n in [gen.nome()]]
        if r.random() < 0.5:
            integrantes.append((r.choice(estudantes)["nome"], "Estudante"))
        x["cv"]["projetos_pesquisa"] = [projeto_lattes(gen.titulo(), ini, fim, integrantes,
                                                       r.choice([None, "FAPES", "CNPq", "CAPES"]))]
        if r.random() < 0.3:
            x["cv"]["projetos_extensao"] = [projeto_lattes(f"Extensão: {gen.titulo()}", ini, "Atual",
                                                           [(x["nome"], "Coordenador")])]
        concl = [{"titulo": f"Orientação concluída mock {slug(x['nome'])[:12]} {j}", "orientando": gen.nome(),
                  "ano": str(r.randint(2015, 2024)), "natureza": "Iniciação Científica"} for j in range(r.choice([0, 1, 2]))]
        if concl:
            x["cv"]["orientacoes"]["concluidas"]["iniciacao_cientifica"] = concl
        if r.random() < 0.3:
            x["cv"]["orientacoes"]["em_andamento"]["dissertacao_de_mestrado"] = [
                {"titulo": f"Dissertação em andamento mock {slug(x['nome'])[:12]}", "orientando": gen.nome(),
                 "ano_inicio": "2025", "ano_conclusao": ""}]

    # cenários válidos específicos
    L["L01"]["cv"]["projetos_pesquisa"].append(projeto_lattes(
        mundo.inits[pj_l01["iid"]]["nome"], pj_l01["ini"].year, "Atual", [(L["L01"]["nome"], "Coordenador"), (gen.nome(), "Integrante")]))
    L["L01"]["cenario"] = "projeto com o mesmo título de um projeto do SigPesq (é juntado)"
    compartilhado = projeto_lattes("Projeto compartilhado mock entre dois currículos", 2021, "2023",
                                   [(L["L02"]["nome"], "Coordenador"), (L["L03"]["nome"], "Integrante")], "FAPES")
    L["L02"]["cv"]["projetos_pesquisa"].append(compartilhado)
    L["L03"]["cv"]["projetos_pesquisa"].append(json.loads(json.dumps(compartilhado)))
    L["L02"]["cenario"] = L["L03"]["cenario"] = "projeto presente em dois currículos (uma iniciativa só)"
    art = artigo([citacao(L["L04"]["nome"]), citacao(L["L05"]["nome"])])
    L["L04"]["cv"]["producao_bibliografica"]["artigos_periodicos"].append(art)
    L["L05"]["cv"]["producao_bibliografica"]["artigos_periodicos"].append(json.loads(json.dumps(art)))
    L["L04"]["cenario"] = L["L05"]["cenario"] = "artigo com o mesmo DOI em dois currículos (uma produção só)"
    assert L["L06"]["nome"] == b06["Orientador"]
    L["L06"]["cv"]["orientacoes"]["concluidas"].setdefault("iniciacao_cientifica", []).append(
        {"titulo": mundo.inits[b06["iid"]]["nome"], "orientando": b06["Orientado"],
         "ano": str((parse_data(b06["Fim"]) or HOJE).year), "natureza": "Iniciação Científica"})
    L["L06"]["cenario"] = "orientação com o mesmo título de um plano do SigPesq (é juntada)"
    co_a, co_b = gen.nome(), gen.nome()
    L["L07"]["cv"]["formacao_academica"].append(
        {"tipo": "Mestrado em Engenharia Elétrica", "nome_instituicao": "Universidade Federal do Espírito Santo",
         "ano_inicio": "2008", "ano_conclusao": "2010",
         "descricao": f"Título: Controle preditivo de microrredes, Ano de Obtenção: 2010. Orientador: {co_a}. Coorientador: {co_b}."})
    L["L07"]["cenario"] = "formação com orientador e coorientador"
    L["L08"]["cv"]["atuacao_profissional"].append(
        {"instituicao": "Prefeitura Municipal de Vila Velha", "ano_inicio": "2005", "ano_fim": "2007",
         "vinculo": "Celetista"})
    L["L08"]["cenario"] = "vínculos com IFES (reaproveita a organização) e órgão público"
    L["L09"]["cv"]["projetos_pesquisa"].append(projeto_lattes("Projeto mock com término previsto para 2027", 2024,
                                                              "2027", [(L["L09"]["nome"], "Coordenador")]))
    L["L09"]["cenario"] = "projeto com ano de conclusão no futuro (2027)"
    L["L10"]["cv"]["orientacoes"]["em_andamento"]["iniciacao_cientifica"] = [
        {"titulo": "Orientação em andamento mock só com ano", "orientando": gen.nome(), "ano": "2025",
         "natureza": "Iniciação Científica"}]
    L["L10"]["cenario"] = "orientação em andamento só com 'ano' (ano de início no Lattes)"

    # exceções
    def novo_cv(lid_nome=None):
        nome = lid_nome or gen.nome()
        lid = gen.id_lattes()
        return nome, lid, cv_base(nome, lid)

    excecoes_l = []
    n, lid, cv = novo_cv()
    cv["informacoes_pessoais"]["texto_resumo"] = ""
    excecoes_l.append({"id": "L41", "cenario": "currículo sem resumo (perfil pulado)", "nome": n, "lattes_id": lid, "cv": cv})
    n, lid, cv = novo_cv()
    cv["informacoes_pessoais"]["atualizacao_cv"] = "31/02/2024"
    excecoes_l.append({"id": "L42", "cenario": "data de atualização inválida (31/02/2024)", "nome": n, "lattes_id": lid, "cv": cv})
    # homônimo do L36 (externo), com ID maior para ser lido depois
    lid_h = str(int(L["L36"]["lattes_id"]) + 1)
    while lid_h in gen._ids_lattes:
        lid_h = str(int(lid_h) + 1)
    gen._ids_lattes.add(lid_h)
    cv = cv_base(L["L36"]["nome"], lid_h)
    cv["informacoes_pessoais"]["nome_citacoes"] = "HOMONIMO, X. Y."
    excecoes_l.append({"id": "L43", "cenario": "homônimo do L36 com outro ID Lattes (vai para revisão)",
                       "nome": L["L36"]["nome"], "lattes_id": lid_h, "cv": cv})
    n, lid, cv = novo_cv()
    del cv["informacoes_pessoais"]["nome_completo"]
    excecoes_l.append({"id": "L44", "cenario": "currículo sem nome", "nome": None, "lattes_id": lid, "cv": cv,
                       "arquivo_nome": f"SemNome_{lid}.json"})
    n, lid, cv = novo_cv()
    excecoes_l.append({"id": "L45", "cenario": "JSON malformado (arquivo truncado)", "nome": n, "lattes_id": lid,
                       "cv": cv, "malformado": True})
    n, lid, cv = novo_cv()
    excecoes_l.append({"id": "L46", "cenario": "arquivo sem ID Lattes no nome", "nome": n, "lattes_id": lid, "cv": cv,
                       "arquivo_nome": "curriculo_mock_sem_id.json"})
    n, lid, cv = novo_cv()
    cv["producao_bibliografica"]["artigos_periodicos"] = [
        artigo([citacao(n)], titulo=""), artigo([citacao(n)], ano=""), artigo([citacao(n)], revista=None, doi=None)]
    cv["projetos_pesquisa"] = [projeto_lattes("Projeto mock sem integrantes", 2022, "Atual", [])]
    excecoes_l.append({"id": "L47", "cenario": "artigos sem título/ano/revista e projeto sem integrantes",
                       "nome": n, "lattes_id": lid, "cv": cv})
    n, lid, cv = novo_cv()
    cv["idiomas"] = [{"nome": "Inglês", "le": "Fluente", "escreve": "", "fala": "Bem", "compreende": "RAZOAVELMENTE"}]
    excecoes_l.append({"id": "L48", "cenario": "idioma com níveis fora do padrão (Fluente, vazio, caixa alta)",
                       "nome": n, "lattes_id": lid, "cv": cv})
    n, lid, cv = novo_cv()
    co_c = gen.nome()
    cv["atuacao_profissional"].append({"instituicao": "Mock Consultoria Ltda", "ano_inicio": "2001", "ano_fim": "2003"})
    cv["formacao_academica"].append({"tipo": "Especialização em Gestão Pública", "nome_instituicao": None})
    cv["formacao_academica"].append({"tipo": "Mestrado em Educação", "nome_instituicao": "Universidade de São Paulo",
                                     "ano_inicio": "2004", "ano_conclusao": "2006",
                                     "descricao": f"Título: Avaliação formativa, Ano de Obtenção: 2006. Coorientador: {co_c}."})
    excecoes_l.append({"id": "L49", "cenario": "atuação sem vínculo, formação sem instituição/ano, só coorientador",
                       "nome": n, "lattes_id": lid, "cv": cv, "coorientador": co_c})
    n, lid, cv = novo_cv()
    cv["projetos_pesquisa"] = [projeto_lattes("Projeto mock com ano numérico", 2020, "2022", [(n, "Coordenador")])]
    cv["projetos_pesquisa"][0]["ano_inicio"] = 2020  # int em vez de texto
    excecoes_l.append({"id": "L50", "cenario": "ano do projeto como número (2020) em vez de texto",
                       "nome": n, "lattes_id": lid, "cv": cv, "sonda_quebra": True})
    for x in excecoes_l:
        x["tipo"] = "excecao"
    todos_l = lattes_def + excecoes_l
    for x in todos_l:
        x["arquivo"] = x.get("arquivo_nome") or f"{slug(x['nome'] or 'sem')[:30]}_{x['lattes_id']}.json"
        caminho = os.path.join(pasta_lattes, x["arquivo"])
        texto = json.dumps(x["cv"], ensure_ascii=False, indent=2)
        if x.get("malformado"):
            texto = texto[: len(texto) // 2]
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(texto)
        gen.catalogar(x["id"], "lattes", f"lattes_json/{x['arquivo']}", x["tipo"], x["cenario"])
    assert L["L06"]["nome"], "cenário L06 não pôde ser montado"

    # --- simulação: Lattes (ordem = nome do arquivo)
    lidos = []
    for x in sorted(todos_l, key=lambda y: os.path.join(pasta_lattes, y["arquivo"])):
        base_nome = x["arquivo"][:-5].split("_")[-1]
        if not base_nome.isdigit() or x.get("malformado"):
            x["esperado_lido"] = False
            continue
        x["esperado_lido"] = True
        lidos.append(x)

    def simular_lattes(curriculos: List[dict], m: Mundo) -> None:
        donos: Dict[str, Tuple[int, str]] = {}
        lattes_por_pessoa = {pid: v["lattes"] for pid, v in m.pessoas.items() if v["lattes"]}
        passo = "lattes_pessoas"
        for x in curriculos:
            info = x["cv"].get("informacoes_pessoais", {})
            nome = (info.get("nome_completo") or "").strip() or None
            pid = next((p for p, v in m.pessoas.items() if v["lattes"] == x["lattes_id"]), None)
            if pid is None:
                if not nome:
                    m.pular(passo, "ValueError: currículo sem nome", f"Lattes {x['lattes_id']}")
                    continue
                pid = m.pessoa(nome)
                outro = lattes_por_pessoa.get(pid)
                if outro and outro != x["lattes_id"]:
                    pid = m._criar(nome, None, registrar_chave=False, ref=f"{nome} [lattes {x['lattes_id']}]")
                    m.revisar(passo, f"homônimo de pessoa com outro Lattes ({outro})", f"{nome} ({x['lattes_id']})")
                m.pessoas[pid]["lattes"] = x["lattes_id"]
            m.contar(passo, "donos")
            resumo = (info.get("texto_resumo") or "").strip()
            cit = (info.get("nome_citacoes") or "").strip()
            try:
                atual = datetime.strptime(info.get("atualizacao_cv") or "", "%d/%m/%Y")
            except ValueError:
                atual = None
            falt = [c for c, v in (("resumo", resumo), ("nomes de citação", cit), ("data de atualização", atual)) if not v]
            if falt:
                m.pular(passo, f"perfil Lattes sem {', '.join(falt)}", nome)
            else:
                m.perfis[pid] = {"resumo": resumo, "nomes_citacao": cit, "atualizado_em": atual.isoformat()}
                m.contar(passo, "perfis")
            donos[x["lattes_id"]] = (pid, nome)
            lattes_por_pessoa[pid] = x["lattes_id"]
        # fase 2
        passo = "lattes_curriculos"
        candidatos = defaultdict(set)
        for pid, v in m.pessoas.items():
            ch = normalizar_texto(v["nome"])
            if ch:
                candidatos[ch].add(pid)
        for pid, pf in m.perfis.items():
            for c in pf["nomes_citacao"].split(";"):
                ch = normalizar_texto(c)
                if ch:
                    candidatos[ch].add(pid)
        indice = {k: next(iter(v)) for k, v in candidatos.items() if len(v) == 1}
        ident_lattes: Dict[str, int] = {}
        for x in curriculos:
            if x["lattes_id"] not in donos:
                m.pular(passo, "dono do currículo não carregado", x["lattes_id"])
                continue
            pid, nome = donos[x["lattes_id"]]
            cv = x["cv"]
            for pr in cv.get("premios_titulos") or []:
                t = (pr.get("descricao") or pr.get("titulo") or "").strip()
                if t:
                    ano = pr.get("ano")
                    m.premios[pid].add((t[:255], int(ano) if str(ano or "").isdigit() else None))
            for idi in cv.get("idiomas") or []:
                nivel = lambda v: NIVEIS.get(str(v or "").strip().capitalize() if str(v or "").strip().lower() in
                                             ("bem", "razoavelmente", "pouco") else "", "nao_se_aplica")
                if idi["nome"] not in m.proficiencias[pid]:
                    m.proficiencias[pid][idi["nome"]] = {
                        "leitura": nivel(idi.get("le")), "escrita": nivel(idi.get("escreve")),
                        "fala": nivel(idi.get("fala")), "compreensao": nivel(idi.get("compreende"))}
            for at in cv.get("atuacao_profissional") or []:
                inst = (at.get("instituicao") or "").strip()
                if not inst:
                    continue
                if not at.get("vinculo"):
                    m.pular(passo, "atuação profissional sem tipo de vínculo", f"{inst} ({nome})")
                    continue
                o = m.org(inst, Mundo.tipo_org_por_nome(inst))
                fim_txt = str(at.get("ano_fim") or "")
                fim = None if fim_txt.lower() in ("atual", "atualmente") else (
                    date(int(fim_txt), 12, 31) if fim_txt.isdigit() else None)
                ini = date(int(at["ano_inicio"]), 1, 1) if str(at.get("ano_inicio") or "").isdigit() else None
                m.vinculos[pid].add((o, at["vinculo"], iso(ini), iso(fim)))
            for fo in cv.get("formacao_academica") or []:
                tipo = fo.get("tipo", "")
                grau, curso = (tipo.split(" em ", 1) + [None])[:2] if " em " in tipo else (tipo or "Unknown", None)
                curso = curso or grau
                inst = fo.get("nome_instituicao") or "Unknown Institution"
                o = m.org(inst, "instituicao_ensino")
                m.tipos_formacao.setdefault(normalizar_texto(grau), grau)
                ai = int(fo["ano_inicio"]) if fo.get("ano_inicio") else 0
                af = int(fo["ano_conclusao"]) if fo.get("ano_conclusao") else None
                desc = fo.get("descricao") or ""
                mt = __import__("re").search(r"Título:\s*(.+?)(?:, Ano|,\s*Orientador|\.|$)", desc, __import__("re").I)
                orient = []
                mo = __import__("re").search(r"(?<!co)(?<!co-)Orientador:\s*([^.;)]+)", desc, __import__("re").I)
                mc = __import__("re").search(r"Co-?orientador:\s*([^.;)]+)", desc, __import__("re").I)
                # negócio: "Coorientador: X" não é orientador
                for achado, papel in ((mo, "orientador"), (mc, "coorientador")):
                    if achado:
                        orient.append((m.pessoa(achado.group(1).strip()), papel))
                m.formacoes[pid].append({"tipo": m.tipos_formacao[normalizar_texto(grau)], "org": o, "curso": curso,
                                         "ano_inicio": ai, "ano_fim": af,
                                         "titulo_tese": mt.group(1).strip() if mt else None,
                                         "orientadores": orient})
            arts = [(a, "artigo") for a in (cv.get("producao_bibliografica") or {}).get("artigos_periodicos", [])]
            arts += [(a, "trabalhos_completos_congressos") for a in
                     (cv.get("producao_bibliografica") or {}).get("trabalhos_completos_congressos", [])]
            for a, tipo in arts:
                titulo = (a.get("titulo") or "").strip()
                if not titulo:
                    m.pular(passo, "artigo sem título", nome)
                    continue
                ano = int(a["ano"]) if str(a.get("ano") or "").isdigit() else 0
                veiculo = (a.get("revista") if tipo == "artigo" else a.get("evento")) or "Não informado"
                doi = (a.get("doi") or None) if tipo == "artigo" else None
                prod = None
                for pr in m.producoes:
                    if pr["artigo"] is None:
                        continue
                    if doi and pr["artigo"]["doi"] == doi:
                        prod = pr
                        break
                if prod is None:
                    prod = next((pr for pr in m.producoes if pr["artigo"] is not None and pr["titulo"] == titulo
                                 and pr["ano"] == ano), None)
                if prod is None:
                    prod = {"titulo": titulo, "ano": ano, "tipo": tipo,
                            "link": f"https://doi.org/{doi}" if doi else None,
                            "artigo": {"veiculo": veiculo, "volume": a.get("volume") if tipo == "artigo" else None,
                                       "paginas": a.get("paginas"), "doi": doi}, "autores": set()}
                    m.producoes.append(prod)
                prod["autores"].add(pid)
                for au in str(a.get("autores") or "").split(";"):
                    co = indice.get(normalizar_texto(au))
                    if co is not None and co != pid:
                        prod["autores"].add(co)
            for cat, itens in (cv.get("producao_tecnica") or {}).items():
                for it in itens:
                    t = (it.get("titulo") or "").strip()
                    ano = int(it["ano"]) if str(it.get("ano") or "").isdigit() else 0
                    prod = next((pr for pr in m.producoes if pr["artigo"] is None and pr["titulo"] == t
                                 and pr["ano"] == ano and pr["tipo"] == cat), None)
                    if prod is None:
                        prod = {"titulo": t, "ano": ano, "tipo": cat, "link": None, "artigo": None, "autores": set()}
                        m.producoes.append(prod)
                    prod["autores"].add(pid)
            projetos = []
            for chave, tipo in (("projetos_pesquisa", "projeto_pesquisa"), ("projetos_extensao", "projeto_extensao"),
                                ("projetos_desenvolvimento", "projeto_desenvolvimento")):
                for pr in cv.get(chave) or []:
                    projetos.append((pr, tipo))
            vistos_t = set()
            for pr, tipo in projetos:
                titulo = (pr.get("nome") or "").strip()
                if not titulo or titulo in vistos_t:
                    continue
                vistos_t.add(titulo)
                ai = pr.get("ano_inicio")
                ai = int(ai) if str(ai or "").isdigit() else None
                fim_txt = str(pr.get("ano_conclusao") or "")
                ativo = fim_txt.lower() == "atual"
                af = int(fim_txt) if fim_txt.isdigit() else None
                ini = date(ai, 1, 1) if ai else None
                fim = date(af, 12, 31) if af else None
                situacao = "em_andamento" if ativo else "concluida"
                bruto = " ".join(pr.get("descricao") or [])
                desc = __import__("re").sub(r"^Descrição:\s*", "", bruto, flags=__import__("re").I)
                for mk in ("Situação:", "Natureza:", "Alunos envolvidos:", "Integrantes:"):
                    desc = desc.split(mk)[0]
                desc = desc.strip().rstrip(".") or None
                coord, pesq, estud = None, [], []
                for it in pr.get("integrantes") or []:
                    papel = it.get("papel", "Integrante").lower()
                    if "coordenador" in papel:
                        if coord is None:
                            coord = it["nome"]
                        else:
                            pesq.append(it["nome"])
                    elif "estudante" in papel or "bolsista" in papel:
                        estud.append(it["nome"])
                    else:
                        pesq.append(it["nome"])
                if coord and chave_pessoa(coord) != chave_pessoa(nome) and not any(
                        chave_pessoa(n) == chave_pessoa(nome) for n in pesq + estud):
                    pesq.append(nome)
                ident = (titulo, coord or nome, ai, tipo)
                existente = ident_lattes.get(ident)
                if existente is None:
                    ids = [i for t in ("projeto_pesquisa", "projeto_extensao", "projeto_desenvolvimento")
                           for i in m.inits_por_nome(titulo, t)]
                    existente = min(ids) if ids else None
                if existente is None:
                    iid = m.nova_init(titulo, tipo, ifes, situacao, desc, ini, fim)
                    m.contar(passo, f"{tipo}_criadas")
                else:
                    iid = existente
                    atual = m.inits[iid]
                    for campo, valor in (("descricao", desc), ("ini", ini), ("fim", fim)):
                        if valor not in (None, "") and atual[campo] in (None, ""):
                            atual[campo] = valor
                    if atual["situacao"] == "desconhecida" and situacao != "desconhecida":
                        atual["situacao"] = situacao
                    m.contar(passo, f"{m.inits[iid]['tipo']}_juntadas")
                ident_lattes[ident] = iid
                x.setdefault("projetos_iid", []).append(iid)
                if coord:
                    m.participante(iid, m.pessoa(coord), "coordenador", ini)
                for n_ in pesq:
                    m.participante(iid, m.pessoa(n_), "pesquisador", ini)
                for n_ in estud:
                    m.participante(iid, m.pessoa(n_), "estudante", ini)
                fins = pr.get("financiadores") or []
                if fins and fins[0].get("nome"):
                    o = m.org(fins[0]["nome"], "fomento")
                    m.inits[iid]["orgs"].add((o, "financiadora"))
        # fase 3
        passo = "lattes_orientacoes"
        for x in curriculos:
            if x["lattes_id"] not in donos:
                m.pular(passo, "dono do currículo não carregado", x["lattes_id"])
                continue
            pid, nome = donos[x["lattes_id"]]
            ori = x["cv"].get("orientacoes") or {}
            for secao, situacao in (("concluidas", "concluida"), ("em_andamento", "em_andamento")):
                for _tipo, itens in (ori.get(secao) or {}).items():
                    for it in itens:
                        titulo, aluno = it.get("titulo"), it.get("orientando")
                        if not (titulo and aluno):
                            continue
                        ai = int(it["ano_inicio"]) if str(it.get("ano_inicio") or "").isdigit() else None
                        fim_txt = it.get("ano_conclusao") or it.get("ano")
                        af = int(fim_txt) if str(fim_txt or "").isdigit() else None
                        ini = date(ai, 1, 1) if ai else None
                        fim = date(af, 12, 31) if af else None
                        ids = m.inits_por_nome(titulo, "orientacao")
                        ident = ("orient", titulo, nome, aluno, ai or af)
                        existente = ident_lattes.get(ident) or (min(ids) if ids else None)
                        if existente is None:
                            iid = m.nova_init(titulo, "orientacao", ifes, situacao, None, ini, fim)
                            m.contar(passo, "orientacao_criadas")
                        else:
                            iid = existente
                            atual = m.inits[iid]
                            for campo, valor in (("ini", ini), ("fim", fim)):
                                if valor is not None and atual[campo] is None:
                                    atual[campo] = valor
                            m.contar(passo, "orientacao_juntadas")
                        ident_lattes[ident] = iid
                        x.setdefault("orientacoes_iid", []).append(iid)
                        m.participante(iid, pid, "orientador", ini)
                        m.participante(iid, m.pessoa(aluno), "orientando", ini)

    curriculos_execucao = [x for x in lidos if not x.get("sonda_quebra")]
    simular_lattes(curriculos_execucao, mundo)

    # ================================================================ GABARITO
    def ref_set(parts: Dict[Tuple[int, str], Any]) -> Dict[str, List[list]]:
        saida_p = defaultdict(list)
        for (pid, papel), ini in parts.items():
            saida_p[papel].append([mundo.ref(pid), iso(ini)])
        return {k: sorted(v) for k, v in saida_p.items()}

    def init_json(iid: int) -> dict:
        v = mundo.inits[iid]
        pai = v["pai"]
        return {
            "nome": v["nome"], "tipo": v["tipo"], "organizacao": v["org"], "situacao": v["situacao"],
            "descricao": v["descricao"], "data_inicio": iso(v["ini"]), "data_fim": iso(v["fim"]),
            "participantes": ref_set(v["parts"]), "areas": sorted(v["areas"]),
            "equipes": sorted([g["nome"], papel] for g, papel in v["equipes"].values()),
            "organizacoes": sorted(list(x) for x in v["orgs"]),
            "pai": mundo.inits[pai]["nome"] if pai else None,
            "bolsas": sorted([mundo.ref(k[0]), list(b)] for k, b in v["bolsas_part"].items()),
        }

    def grupo_json(g: dict) -> dict:
        return {"nome": g["nome"], "sigla": g["sigla"], "descricao": g["descricao"], "unidade": g["unidade"],
                "url_cnpq": g["url"], "data_inicio": iso(g["data_inicio"]), "areas": sorted(g["areas"]),
                "membros": sorted([mundo.ref(pid), papel, iso(d[0]), iso(d[1])] for (pid, papel), d in g["membros"].items())}

    registros_esp = {}
    for g in linhas_grupo:
        e_ = dict(g["esperado"])
        if e_.get("carregado") or e_.get("repetido"):
            e_["grupo"] = grupo_json(g["obj"])
        registros_esp[g["id"]] = {"linha": g["linha"], **e_}
    for p in linhas_proj:
        e_ = dict(p["esperado"])
        if e_.get("carregado"):
            e_["iniciativa"] = init_json(p["iid"])
            e_["codigo"] = p.get("codigo_norm")
        else:
            e_["titulo"] = p["Titulo"]
        if p.get("grupo_criado") is not None:
            e_["grupo_criado"] = grupo_json(p["grupo_criado"])
        registros_esp[p["id"]] = {"linha": p["linha"], **e_}
    for b in linhas_bols:
        e_ = dict(b["esperado"])
        if e_.get("carregado"):
            e_["iniciativa"] = init_json(b["iid"])
            e_["cod_pt"] = b["CodPT"]
            if b.get("bolsa_chave"):
                e_["bolsa"] = mundo.bolsas[b["bolsa_chave"]]
        registros_esp[b["id"]] = {"linha": b["linha"], **e_}
    for c in cnpq_def:
        e_ = {"url": c["url"], "grupo_antes": c["nome_antes"], "grupo": grupo_json(c["grupo"]),
              "indisponivel": "__erro__" in c["esp"]}
        registros_esp[c["id"]] = e_
    for x in todos_l:
        e_ = {"arquivo": x["arquivo"], "lattes_id": x["lattes_id"], "lido": x.get("esperado_lido", False),
              "sonda_quebra": bool(x.get("sonda_quebra"))}
        pid = next((p for p, v in mundo.pessoas.items() if v["lattes"] == x["lattes_id"]), None)
        if pid is not None:
            e_["pessoa"] = mundo.ref(pid)
            e_["perfil"] = mundo.perfis.get(pid)
            e_["premios"] = sorted([t, a] for t, a in mundo.premios.get(pid, set()))
            e_["proficiencias"] = mundo.proficiencias.get(pid, {})
            e_["vinculos"] = sorted(list(v) for v in mundo.vinculos.get(pid, set()))
            e_["formacoes"] = sorted(
                [f["tipo"], f["org"], f["curso"], f["ano_inicio"], f["ano_fim"], f["titulo_tese"],
                 sorted([mundo.ref(op), pp] for op, pp in f["orientadores"])] for f in mundo.formacoes.get(pid, []))
            e_["producoes"] = sorted(
                [pr["titulo"], pr["ano"], pr["tipo"], pr["link"],
                 pr["artigo"], sorted(mundo.ref(a) for a in pr["autores"])]
                for pr in mundo.producoes if pid in pr["autores"])
            e_["projetos"] = [init_json(i) for i in sorted(set(x.get("projetos_iid", [])))]
            e_["orientacoes"] = [init_json(i) for i in sorted(set(x.get("orientacoes_iid", [])))]
        registros_esp[x["id"]] = e_

    totais = {
        "pessoas_com_nome": len(mundo.pessoas),
        "iniciativas_por_tipo": dict(sorted(
            {t: sum(1 for v in mundo.inits.values() if v["tipo"] == t) for t in
             {v["tipo"] for v in mundo.inits.values()}}.items())),
        "equipes": len(mundo.grupos),
        "grupos_com_url": sum(1 for g in mundo.grupos if g["url"]),
        "unidades": sorted(mundo.unidades),
        "organizacoes": sorted([o["nome"], o["tipo"]] for o in mundo.orgs),
        "bolsas": sorted([b["nome"], b["financiador"], b["valor"]] for b in mundo.bolsas.values()),
        "areas": sorted(mundo.areas.values()),
        "producoes": len(mundo.producoes),
        "areas_pessoa": sorted([mundo.ref(p), a] for p, a in mundo.areas_pessoa),
        "emails_por_pessoa": {mundo.ref(p): sorted(v["emails_fonte"]) for p, v in mundo.pessoas.items()
                              if v["emails_fonte"]},
        "emails_gravados_por_pessoa": {mundo.ref(p): sorted(v["emails_db"]) for p, v in mundo.pessoas.items()
                                       if v["emails_db"]},
        "pessoas": sorted(v["ref"] for v in mundo.pessoas.values()),
    }
    gabarito = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "data_referencia": HOJE.isoformat(),
        "semente": semente,
        "observacao": "estado esperado da execução principal (todos os registros, exceto a sonda L50, "
                      "que interrompe a carga e é validada numa execução à parte)",
        "registros": registros_esp,
        "totais": totais,
        "pendencias": mundo.pendencias,
        "revisoes": mundo.revisoes,
        "contagens": {k: dict(v) for k, v in mundo.contagens.items()},
        "alertas_negocio": mundo.alertas_negocio,
        "sonda": {"arquivo": next(x["arquivo"] for x in todos_l if x.get("sonda_quebra"))},
    }
    with open(os.path.join(saida, "gabarito.json"), "w", encoding="utf-8") as fh:
        json.dump(gabarito, fh, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(saida, "catalogo_registros.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "fonte", "arquivo", "tipo_caso", "cenario"])
        w.writeheader()
        w.writerows(gen.registros)

    resumo = defaultdict(lambda: defaultdict(int))
    for reg in gen.registros:
        resumo[reg["fonte"]][reg["tipo_caso"]] += 1
    total = len(gen.registros)
    print(f"{total} registros gerados em {saida}")
    for fonte, cont in resumo.items():
        print(f"  {fonte:20s} válidos={cont['valido']:3d}  exceções={cont['excecao']:3d}")
    assert total == 300, total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", default="dados")
    ap.add_argument("--semente", type=int, default=20261014)
    args = ap.parse_args()
    gerar(args.saida, args.semente)
