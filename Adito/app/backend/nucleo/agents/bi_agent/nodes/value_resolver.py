"""Acha na pergunta os valores reais do banco (campus, programa, área, título...) sem chamar LLM.

Substitui o resolvedor ReAct e o rewriter: a pergunta não é mais reescrita. Os valores encontrados
entram no prompt do gerador como um bloco à parte, e o modelo decide se usa.

Passos, todos locais e determinísticos:
1. quebra a pergunta em trechos de 1 a 4 palavras (sem números e sem palavras de métrica nas pontas);
2. sinônimos e siglas do contexto (`sinonimos.json`), por texto normalizado;
3. valor idêntico ao do catálogo (sem acento e sem caixa);
4. o resto vai num lote só para o modelo local e é comparado por cosseno com os vetores do dados.db.
Trechos que se sobrepõem ficam com o de maior similaridade.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from analytics_index.valores import indice_valores, normalizar_texto
from core.contexts import get_contexto
from core.datastore import REPO_APP_DIR, data_dir
from core.rich_logging import log_kv, log_node_end, log_node_start, log_warning

from ..state import BiAgentState

MAX_PALAVRAS = 4
POR_TRECHO = 3
MAX_VALORES = 12
# shortcut: limite provisório; calibrar com o teste de busca do dados.db real (scripts/teste_busca_valores.py).
SIMILARIDADE_MINIMA = float(os.getenv("ADITO_VALOR_SIMILARIDADE_MIN", "0.80"))
# Num mesmo trecho, fica quem estiver a até isso do melhor (ex.: "Serra" em várias views).
MARGEM_NO_TRECHO = 0.03

# Palavras que nunca começam nem terminam um trecho (podem ficar no meio: "ciência da computação").
PALAVRAS_VAZIAS = frozenset("""
a o as os um uma uns umas de da do das dos e ou em no na nos nas ao aos por pela pelo pelas pelos para pra
com sem sob sobre entre ate desde que qual quais quanto quanta quantos quantas como onde quando cujo
me mostre mostra liste lista listar exiba informe diga traga ver veja quero gostaria pode poderia
total totais quantidade numero contagem media soma ranking maior maiores menor menores mais menos top
existe existem ha tem tinha teve tiveram possui possuem foram foi sao era eram esta estao ja ainda
cada todo toda todos todas geral ao todo ano anos mes meses periodo atual atuais ultimo ultimos
projeto projetos acao acoes grupo grupos orientacao orientacoes bolsa bolsas producao producoes
pesquisador pesquisadores estudante estudantes aluno alunos campus campi ifes base dados registro registros
""".split())


def _tokens(texto: str) -> list[str]:
    return re.findall(r"\w+", normalizar_texto(texto))


def trechos(texto: str) -> list[tuple[int, int, str]]:
    """(início, fim, texto) de cada trecho candidato, em palavras normalizadas."""
    palavras = _tokens(texto)
    saida = []
    for n in range(1, MAX_PALAVRAS + 1):
        for i in range(len(palavras) - n + 1):
            janela = palavras[i:i + n]
            if janela[0] in PALAVRAS_VAZIAS or janela[-1] in PALAVRAS_VAZIAS:
                continue
            if any(p.isdigit() for p in janela):
                continue
            saida.append((i, i + n, " ".join(janela)))
    return saida


@lru_cache(maxsize=8)
def _sinonimos_do_arquivo(caminho: str, mtime: float) -> dict[str, list[dict]]:
    """termo normalizado → [{"coluna", "valores"}]."""
    entradas = json.loads(Path(caminho).read_text(encoding="utf-8")).get("sinonimos", [])
    mapa: dict[str, list[dict]] = {}
    for entrada in entradas:
        for termo in entrada.get("termos", []):
            mapa.setdefault(" ".join(_tokens(termo)), []).append(
                {"coluna": entrada["coluna"], "valores": entrada["valores"]}
            )
    return mapa


def sinonimos_do_contexto(contexto_id) -> dict[str, list[dict]]:
    contexto = get_contexto(contexto_id)
    if contexto is None:
        return {}
    for base in (data_dir() / "contexts", REPO_APP_DIR / "contexts"):
        arquivo = base / contexto.slug / "sinonimos.json"
        if arquivo.exists():
            return _sinonimos_do_arquivo(str(arquivo), arquivo.stat().st_mtime)
    return {}


def resolver_valores(textos: list[str], indice, embedder, sinonimos: dict, views: set[str] | None = None) -> list[dict]:
    candidatos: list[tuple[int, int, str]] = []
    for texto in textos:
        for t in trechos(texto):
            if t not in candidatos:
                candidatos.append(t)

    achados: dict[tuple[int, int, str], list[dict]] = {}
    catalogo = indice.catalogo() if indice.disponivel else {}
    restantes = []
    for trecho in candidatos:
        termo = trecho[2]
        hits = [
            {"coluna": s["coluna"], "valor": v, "views": [], "similaridade": 1.0, "origem": "sinônimo"}
            for s in sinonimos.get(termo, [])
            for v in s["valores"]
        ]
        for (view, coluna), valores in catalogo.items():
            if (views is None or view in views) and termo in valores:
                hits.append({"coluna": coluna, "valor": valores[termo], "views": [view], "similaridade": 1.0,
                             "origem": "idêntico"})
        if hits:
            achados[trecho] = hits
        else:
            restantes.append(trecho)

    if restantes and indice.disponivel and embedder is not None:
        consultas = embedder.matriz([t[2] for t in restantes], pergunta=True)
        for trecho, hits in zip(restantes, indice.buscar(consultas, SIMILARIDADE_MINIMA, POR_TRECHO, views)):
            if hits:
                achados[trecho] = [
                    {"coluna": h["coluna"], "valor": h["valor"], "views": [h["view"]],
                     "similaridade": h["similaridade"], "origem": "semântico"}
                    for h in hits
                ]

    # Sobreposição: o trecho de maior similaridade (e, no empate, o mais longo) fica com as palavras.
    ordem = sorted(achados, key=lambda t: (-max(h["similaridade"] for h in achados[t]), -(t[1] - t[0])))
    usados: set[int] = set()
    resultado: list[dict] = []
    for trecho in ordem:
        ini, fim, termo = trecho
        if usados & set(range(ini, fim)):
            continue
        usados |= set(range(ini, fim))
        melhor = max(h["similaridade"] for h in achados[trecho])
        juntos: dict[tuple[str, str], dict] = {}
        for h in achados[trecho]:
            if h["similaridade"] < melhor - MARGEM_NO_TRECHO:
                continue
            chave = (h["coluna"], h["valor"])
            if chave in juntos:
                juntos[chave]["views"] = sorted(set(juntos[chave]["views"]) | set(h["views"]))
            else:
                juntos[chave] = {"termo": termo, **h}
        resultado.extend(juntos.values())
    return resultado[:MAX_VALORES]


def bloco_valores(valores: list[dict]) -> str:
    if not valores:
        return ""
    linhas = []
    for v in valores:
        onde = f" (em {', '.join(v['views'])})" if v["views"] else ""
        literal = v["valor"].replace("'", "''")
        linhas.append(f"- \"{v['termo']}\" → {v['coluna']} = '{literal}'{onde}")
    return (
        "REAL VALUES FOUND IN THE DATABASE for terms of the question (exact stored values; use them only when "
        "the question really refers to them, and keep the business rules for LIKE on aggregated columns):\n"
        + "\n".join(linhas)
    )


def value_resolver(state: BiAgentState, embedder) -> dict[str, object]:
    textos = [state["user_input"]]
    original = (state.get("pergunta_original") or "").strip()
    if original and original != state["user_input"].strip():
        textos.append(original)
    log_node_start("value_resolver", f"pergunta={state['user_input'][:120]!r}")

    indice = indice_valores()
    if not indice.disponivel:
        log_warning("value_resolver", f"Busca semântica desligada: {indice.motivo}")
    contexto = get_contexto(state.get("contexto_id"))
    views = set(contexto.view_names()) if contexto else None
    try:
        valores = resolver_valores(textos, indice, embedder, sinonimos_do_contexto(state.get("contexto_id")), views)
    except Exception as exc:  # modelo local indisponível: segue sem valores, sem travar a pergunta
        log_warning("value_resolver", f"Falha ao resolver valores ({exc}); seguindo sem eles.")
        valores = []
    if valores:
        log_kv("value_resolver", "Valores reais", {
            "valores": [f"{v['similaridade']:.3f} {v['origem']} {v['termo']!r} → {v['coluna']}={v['valor']!r}" for v in valores]
        })
    log_node_end("value_resolver", f"{len(valores)} valor(es)")
    return {"valores_reais": valores}
