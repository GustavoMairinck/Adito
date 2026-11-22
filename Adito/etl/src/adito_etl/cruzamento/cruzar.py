"""Liga as pessoas entre as fontes pelo nome (US-ETL-06), com a inferência do horizon_etl.

Regras:
- BR02: dois nomes são a mesma pessoa quando coincide a forma canônica, a forma
  sem partículas ("dos", "da"...; "Jr" = "Junior") ou as mesmas palavras em outra
  ordem (`normalizar.py`). A ligação é transitiva: se A = B por uma regra e
  B = C por outra, A, B e C são a mesma pessoa.
- Nome não plausível (menos de duas palavras fora títulos: "Dr", "Maria") não
  liga a nada e fica fora de `pessoas.json`; aparece no relatório.
- BR03: se uma fonte com id próprio de pessoa (Lattes) tiver dois ids diferentes
  no mesmo grupo de nomes, são homônimos: não liga, cada (fonte, id) vira uma
  entrada separada e o caso vai para o relatório.
- BR05: o id opaco é `p_` + 16 caracteres base32 do SHA-256 da menor forma sem
  partículas do grupo (estável entre execuções; não carrega CPF, e-mail nem hash deles).

Saídas (determinísticas, sem data/hora):
    trabalho/pessoas.json
    trabalho/relatorio_cruzamento.json   (listas completas)
    trabalho/relatorio_cruzamento.md     (resumo legível)
"""

from __future__ import annotations

import base64
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

from ..comum import base_dir, gravar_json, trabalho_dir
from .leitores import LEITORES, Ocorrencia
from .normalizar import forma_canonica, forma_invariante, forma_ordenada, nome_implausivel

Log = Callable[[str], None]
LIMITE_MD = 50  # nomes listados por seção no .md (o .json tem tudo)


def id_opaco(chave: str) -> str:
    """`p_` + 16 caracteres base32 (a-z, 2-7) do SHA-256 da chave.

    Base32 e não hex: em hex, ids como `p_22291004354...` têm 11 dígitos seguidos
    e caem na trava de PII (padrão de CPF/celular).
    """
    digest = hashlib.sha256(chave.encode("utf-8")).digest()[:10]
    return "p_" + base64.b32encode(digest).decode("ascii").lower()


@dataclass
class Resultado:
    fontes: list[str]
    fontes_sem_leitor: list[str]
    pessoas: list[dict[str, Any]]
    ocorrencias_por_fonte: dict[str, int] = field(default_factory=dict)
    implausiveis: dict[str, int] = field(default_factory=dict)


def _pessoa(ocs: list[Ocorrencia], chave: str, ambiguo: bool) -> dict[str, Any]:
    # Nome exibido: o do titular quando a fonte tem id próprio (nome completo do
    # Lattes); depois prefere a grafia sem vírgula ("SILVA, João" é forma de
    # citação), não toda em maiúsculas, mais frequente e com acentos.
    nomes = Counter(" ".join(o.nome.split()) for o in ocs)
    titulares = {" ".join(o.nome.split()) for o in ocs if o.id_fonte}
    nome = min(nomes.items(), key=lambda kv: (
        kv[0] not in titulares, "," in kv[0], kv[0].isupper(), -kv[1],
        -sum(not c.isascii() for c in kv[0]), kv[0]))[0]
    por_fonte: dict[str, list[dict[str, str]]] = defaultdict(list)
    for o in sorted(set(ocs), key=lambda o: (o.fonte, o.papel, o.ref, o.id_fonte or "", o.nome)):
        item = {"papel": o.papel, "ref": o.ref}
        if o.id_fonte:
            item["id_fonte"] = o.id_fonte
        if item not in por_fonte[o.fonte]:
            por_fonte[o.fonte].append(item)
    pessoa: dict[str, Any] = {
        "id": id_opaco(chave),
        "nome": nome,
        "nome_normalizado": forma_canonica(nome),
    }
    variantes = sorted({forma_canonica(o.nome) for o in ocs})
    if len(variantes) > 1:
        pessoa["variantes"] = variantes
    pessoa["fontes"] = {f: por_fonte[f] for f in sorted(por_fonte)}
    if ambiguo:
        pessoa["ambiguo"] = True
    return pessoa


def _grupos_de_formas(formas: list[str]) -> list[list[str]]:
    """Une formas canônicas que coincidem sem partículas ou em outra ordem
    (union-find; o resultado não depende da ordem de entrada)."""
    pai = {f: f for f in formas}

    def raiz(f: str) -> str:
        while pai[f] != f:
            pai[f] = pai[pai[f]]
            f = pai[f]
        return f

    for chave in (forma_invariante, forma_ordenada):
        primeiro: dict[str, str] = {}
        for f in sorted(formas):
            k = chave(f)
            if k in primeiro:
                a, b = raiz(primeiro[k]), raiz(f)
                if a != b:
                    pai[max(a, b)] = min(a, b)
            else:
                primeiro[k] = f
    grupos: dict[str, list[str]] = defaultdict(list)
    for f in sorted(formas):
        grupos[raiz(f)].append(f)
    return [grupos[r] for r in sorted(grupos)]


def separar_implausiveis(ocorrencias: list[Ocorrencia]) -> tuple[list[Ocorrencia], list[Ocorrencia]]:
    validas, implausiveis = [], []
    for o in ocorrencias:
        (implausiveis if nome_implausivel(o.nome) else validas).append(o)
    return validas, implausiveis


def ligar(ocorrencias: list[Ocorrencia]) -> list[dict[str, Any]]:
    """Agrupa as ocorrências em pessoas (BR02) aplicando a trava de homônimos (BR03).
    Nomes não plausíveis são ignorados aqui; use `separar_implausiveis` para listá-los."""
    por_forma: dict[str, list[Ocorrencia]] = defaultdict(list)
    for o in ocorrencias:
        forma = forma_canonica(o.nome)
        if forma and not nome_implausivel(o.nome):
            por_forma[forma].append(o)

    pessoas = []
    for formas in _grupos_de_formas(list(por_forma)):
        ocs = [o for f in formas for o in por_forma[f]]
        chave = min(forma_invariante(f) for f in formas)
        ids_por_fonte: dict[str, set[str]] = defaultdict(set)
        for o in ocs:
            if o.id_fonte:
                ids_por_fonte[o.fonte].add(o.id_fonte)
        if not any(len(ids) > 1 for ids in ids_por_fonte.values()):
            pessoas.append(_pessoa(ocs, chave, ambiguo=False))
            continue
        grupos: dict[tuple[str, str], list[Ocorrencia]] = defaultdict(list)
        for o in ocs:
            grupos[(o.fonte, o.id_fonte or "")].append(o)
        for (fonte, idf) in sorted(grupos):
            pessoas.append(_pessoa(grupos[(fonte, idf)], f"{chave}|{fonte}|{idf}", ambiguo=True))
    pessoas.sort(key=lambda p: (p["nome_normalizado"], p["id"]))
    return pessoas


def coletar(brutos: Path, log: Log = print) -> tuple[list[str], list[str], list[Ocorrencia]]:
    fontes, sem_leitor, ocorrencias = [], [], []
    if not brutos.exists():
        return fontes, sem_leitor, ocorrencias
    for pasta in sorted(p for p in brutos.iterdir() if p.is_dir()):
        leitor = LEITORES.get(pasta.name)
        if leitor is None:
            sem_leitor.append(pasta.name)
            continue
        ocs = list(leitor(pasta))
        if ocs:
            fontes.append(pasta.name)
            ocorrencias.extend(ocs)
            log(f"{pasta.name}: {len(ocs)} ocorrências de pessoa")
    return fontes, sem_leitor, ocorrencias


def relatorio(res: Resultado) -> dict[str, Any]:
    """Números e listas do relatório (BR03/FR13)."""
    ligaveis = [p for p in res.pessoas if not p.get("ambiguo")]
    pessoas_por_fonte = {f: sum(1 for p in ligaveis if f in p["fontes"]) for f in res.fontes}
    pares = {}
    for a, b in combinations(res.fontes, 2):
        pares[f"{a}+{b}"] = sum(1 for p in ligaveis if a in p["fontes"] and b in p["fontes"])
    sem_par = {
        f: sorted(p["nome"] for p in ligaveis if list(p["fontes"]) == [f])
        for f in res.fontes
    } if len(res.fontes) > 1 else {}
    ambiguos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in res.pessoas:
        if p.get("ambiguo"):
            ambiguos[p["nome_normalizado"]].append({"id": p["id"], "fontes": p["fontes"]})
    return {
        "fontes_lidas": res.fontes,
        "fontes_sem_leitor": res.fontes_sem_leitor,
        "ocorrencias_por_fonte": res.ocorrencias_por_fonte,
        "pessoas_por_fonte": pessoas_por_fonte,
        "pessoas_total": len(res.pessoas),
        "ligadas_por_par": pares,
        "ligadas_em_mais_de_uma_fonte": sum(1 for p in ligaveis if len(p["fontes"]) > 1),
        "sem_par_por_fonte": sem_par,
        "ambiguos": {k: ambiguos[k] for k in sorted(ambiguos)},
        "ligadas_por_variante": sum(1 for p in ligaveis if "variantes" in p),
        "nomes_implausiveis": res.implausiveis,
    }


def _markdown(rel: dict[str, Any]) -> str:
    l = ["# Relatório do cruzamento de pessoas", "",
         "Gerado por `adito-etl cruzar`. Lista completa em `relatorio_cruzamento.json`.", "",
         "## Fontes", "",
         f"- Lidas: {', '.join(rel['fontes_lidas']) or 'nenhuma'}"]
    if rel["fontes_sem_leitor"]:
        l.append(f"- Com bruto, mas sem leitor ainda: {', '.join(rel['fontes_sem_leitor'])}")
    l += ["", "| Fonte | Ocorrências | Pessoas |", "|---|---:|---:|"]
    for f in rel["fontes_lidas"]:
        l.append(f"| {f} | {rel['ocorrencias_por_fonte'].get(f, 0)} | {rel['pessoas_por_fonte'][f]} |")
    l += ["", f"Pessoas no total: {rel['pessoas_total']}. "
              f"Ligadas em mais de uma fonte: {rel['ligadas_em_mais_de_uma_fonte']}.", "",
          "## Ligadas por par de fontes", ""]
    if rel["ligadas_por_par"]:
        l += ["| Par | Pessoas |", "|---|---:|"]
        l += [f"| {k} | {v} |" for k, v in rel["ligadas_por_par"].items()]
    else:
        l.append("Só uma fonte lida; nada para ligar.")
    l += ["", "## Sem par", ""]
    for f, nomes in rel["sem_par_por_fonte"].items():
        l.append(f"### {f} ({len(nomes)})")
        l.append("")
        l += [f"- {n}" for n in nomes[:LIMITE_MD]]
        if len(nomes) > LIMITE_MD:
            l.append(f"- … mais {len(nomes) - LIMITE_MD} no JSON")
        l.append("")
    l += ["## Ligadas por grafia diferente", "",
          f"{rel['ligadas_por_variante']} pessoas juntaram grafias que só coincidem sem partículas "
          "(\"dos\", \"da\"...), com \"Jr\" = \"Junior\" ou com as palavras em outra ordem. "
          "Veja `variantes` em `pessoas.json`.", ""]
    l += ["## Nomes não plausíveis (não ligados)", ""]
    if not rel["nomes_implausiveis"]:
        l.append("Nenhum.")
    l += [f"- `{n}` ({c}x)" for n, c in list(rel["nomes_implausiveis"].items())[:LIMITE_MD]]
    l.append("")
    l += ["## Ambíguos (não ligados)", ""]
    if not rel["ambiguos"]:
        l.append("Nenhum.")
    for forma, entradas in rel["ambiguos"].items():
        l.append(f"- `{forma}`: {len(entradas)} entradas ({', '.join(e['id'] for e in entradas)})")
    return "\n".join(l) + "\n"


def cruzar(log: Log = print) -> dict[str, Any]:
    """Lê `brutos/`, liga as pessoas e grava pessoas + relatório em `trabalho/`."""
    fontes, sem_leitor, ocorrencias = coletar(base_dir() / "brutos", log)
    if not fontes:
        raise FileNotFoundError("nenhum bruto com pessoas em etl/brutos/: rode os extratores antes")
    validas, implausiveis = separar_implausiveis(ocorrencias)
    contagem = Counter(" ".join(o.nome.split()) for o in implausiveis)
    res = Resultado(fontes, sem_leitor, ligar(validas),
                    dict(Counter(o.fonte for o in ocorrencias)),
                    {n: contagem[n] for n in sorted(contagem)})
    rel = relatorio(res)
    destino = trabalho_dir()
    gravar_json(destino / "pessoas.json", res.pessoas)
    gravar_json(destino / "relatorio_cruzamento.json", rel)
    (destino / "relatorio_cruzamento.md").write_text(_markdown(rel), encoding="utf-8")
    return rel
