"""Escolhe os exemplos SQL mais próximos da pergunta, com o modelo de embedding local.

DDL e `rules.md` já vão inteiros no system_prompt, então não passam por busca. Os exemplos do
`examples.json` e os itens manuais da Base de conhecimento são embedados na máquina do usuário
(só a pergunta de cada exemplo), com cache em memória: nenhuma chamada de API.
"""
import hashlib
import json
import logging

import numpy as np

from core.contexts import ORIGEM_MANUAL, get_contexto
from core.datastore import REPO_APP_DIR, data_dir
from core.db import to_db_id
from core.records import KnowledgeItem
from core.rich_logging import log_kv, log_node_end, log_node_start, log_warning

from ..config import KNOWLEDGE_LABELS
from ..state import BiAgentState

logger = logging.getLogger(__name__)

MAX_EXEMPLOS = 4
MIN_EXEMPLOS = 2
# Fica quem estiver a até MARGEM do melhor (cosseno). Relativo, então não depende da escala do modelo.
MARGEM_EXEMPLOS = 0.10
FALLBACK_EXEMPLOS = 8
MANUAL_LIMIT = 10
MANUAL_MAX_CHARS = 800


def _ids(tenant_id, contexto_id) -> list:
    try:
        cid = to_db_id(contexto_id)
    except ValueError:
        cid = None
    return [cid, to_db_id(tenant_id)]


def _exemplos_do_arquivo(contexto_id) -> list[dict]:
    contexto = get_contexto(contexto_id)
    if contexto is None:
        return []
    for base in (data_dir() / "contexts", REPO_APP_DIR / "contexts"):
        arquivo = base / contexto.slug / "examples.json"
        if arquivo.exists():
            try:
                itens = json.loads(arquivo.read_text(encoding="utf-8"))
            except ValueError:
                return []
            return [
                {"pergunta": ex["question"], "texto": f"Pergunta: {ex['question']}\nSQL: {ex['sql']}"}
                for ex in itens
                if "question" in ex and "sql" in ex
            ]
    return []


def _itens_manuais(tenant_id, contexto_id) -> list[KnowledgeItem]:
    try:
        return KnowledgeItem.select(
            "(contexto_id = ? OR contexto_id IS NULL) AND tenant_id = ? "
            "AND (COALESCE(json_extract(metadata, '$.source'), '') = ? OR contexto_id IS NULL)",
            [*_ids(tenant_id, contexto_id), ORIGEM_MANUAL],
            order="created_at DESC, rowid DESC",
            limit=MANUAL_LIMIT,
        )
    except Exception as exc:
        logger.warning("Falha ao carregar itens manuais: %s", exc)
        return []


def _conhecimento_manual(itens: list[KnowledgeItem], system_prompt: str) -> str:
    """Esquema e regras postos à mão no painel vão inteiros (cortados), como as regras do contexto."""
    por_tipo: dict[str, list[str]] = {}
    for item in itens:
        texto = (item.content or "").strip()
        if item.item_type == "query_example" or not texto or texto in system_prompt:
            continue
        por_tipo.setdefault(item.item_type, []).append(texto[:MANUAL_MAX_CHARS])
    return "\n\n".join(
        f"### {KNOWLEDGE_LABELS.get(tipo, tipo)} (manual)\n" + "\n\n".join(textos)
        for tipo, textos in por_tipo.items()
    )


_cache_vetores: dict[str, np.ndarray] = {}


def _vetores(embedder, textos: list[str]) -> np.ndarray:
    """Vetores dos exemplos, embedados uma vez por texto e modelo."""
    chave = lambda t: hashlib.sha256(f"{embedder.modelo.chave}\n{t}".encode()).hexdigest()
    faltam = [t for t in textos if chave(t) not in _cache_vetores]
    if faltam:
        for texto, vetor in zip(faltam, embedder.matriz(faltam)):
            _cache_vetores[chave(texto)] = vetor
    return np.vstack([_cache_vetores[chave(t)] for t in textos])


def escolher_exemplos(embedder, pergunta: str, exemplos: list[dict]) -> list[dict]:
    if len(exemplos) <= MIN_EXEMPLOS:
        return exemplos
    matriz = _vetores(embedder, [ex["pergunta"] for ex in exemplos])
    sims = matriz @ embedder.matriz([pergunta], pergunta=True)[0]
    ordem = np.argsort(-sims)
    melhor = sims[ordem[0]]
    escolhidos = [i for i in ordem[:MAX_EXEMPLOS] if sims[i] >= melhor - MARGEM_EXEMPLOS]
    escolhidos = escolhidos if len(escolhidos) >= MIN_EXEMPLOS else list(ordem[:MIN_EXEMPLOS])
    return [{**exemplos[i], "similaridade": float(sims[i])} for i in escolhidos]


def query_extractor(state: BiAgentState, embedder) -> dict[str, str]:
    pergunta = state["user_input"]
    log_node_start("extractor", f"pergunta={pergunta[:100]!r}")
    tenant_id, contexto_id = state["tenant_id"], state.get("contexto_id")
    system_prompt = state.get("system_prompt") or ""

    manuais = _itens_manuais(tenant_id, contexto_id)
    exemplos = _exemplos_do_arquivo(contexto_id) + [
        {
            "pergunta": (item.metadata or {}).get("question") or item.content,
            "texto": item.content,
        }
        for item in manuais
        if item.item_type == "query_example"
    ]

    escolhidos = exemplos[:FALLBACK_EXEMPLOS]
    modo = "sem modelo local"
    if embedder is not None and exemplos:
        try:
            escolhidos = escolher_exemplos(embedder, pergunta, exemplos)
            modo = "modelo local"
        except Exception as exc:  # modelo ainda não baixado ou corrompido: segue com os primeiros
            log_warning("extractor", f"Modelo local indisponível ({exc}); usando os {FALLBACK_EXEMPLOS} primeiros exemplos.")

    partes = []
    if escolhidos:
        partes.append(f"### {KNOWLEDGE_LABELS['query_example']}\n" + "\n\n".join(ex["texto"] for ex in escolhidos))
    manual = _conhecimento_manual(manuais, system_prompt)
    if manual:
        partes.append(manual)
    contexto = "\n\n".join(partes)
    log_kv(
        "bi",
        "Exemplos escolhidos",
        {"exemplos": [f"{ex.get('similaridade', 0):.3f} {ex['pergunta'][:80]}" for ex in escolhidos]},
    )
    log_node_end("extractor", f"{len(escolhidos)} exemplo(s), {len(contexto)} chars ({modo})")
    return {"retrieved_schema": contexto}
