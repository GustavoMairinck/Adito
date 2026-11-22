import json
from typing import Any

from langchain_core.embeddings import Embeddings

from core.contexts import get_contexto
from core.datastore import REPO_APP_DIR, data_dir
from core.db import to_db_id
from core.records import KnowledgeItem
from core.rich_logging import log_kv, log_node_end, log_node_start
from core.vectors import nearest

from ..config import KNOWLEDGE_LABELS, KNOWLEDGE_LIMITS
from ..state import BiAgentState


def _fallback_examples_for_contexto(contexto_id: str | None) -> str:
    """Se o RAG vetorial ainda não foi indexado, carrega os exemplos do examples.json do contexto."""
    contexto = get_contexto(contexto_id)
    if contexto is None:
        return ""
    for base in (data_dir() / "contexts", REPO_APP_DIR / "contexts"):
        examples_file = base / contexto.slug / "examples.json"
        if examples_file.exists():
            try:
                examples = json.loads(examples_file.read_text(encoding="utf-8"))
                formatted = "\n\n".join(
                    f"Pergunta: {ex['question']}\nSQL: {ex['sql']}"
                    for ex in examples[:16]
                    if "question" in ex and "sql" in ex
                )
                return f"### {KNOWLEDGE_LABELS['query_example']}\n{formatted}" if formatted else ""
            except Exception:
                return ""
    return ""


# Itens do contexto da conversa mais os genéricos (sem contexto).
_DO_CONTEXTO = "(contexto_id = ? OR contexto_id IS NULL) AND tenant_id = ? AND embedding IS NOT NULL"


def _ids(tenant_id, contexto_id) -> list:
    try:
        cid = to_db_id(contexto_id)
    except ValueError:
        cid = None
    return [cid, to_db_id(tenant_id)]


def _search_knowledge(tenant_id: str, contexto_id: str | None, query_embedding: Any, item_type: str):
    items = KnowledgeItem.select(_DO_CONTEXTO + " AND item_type = ?", [*_ids(tenant_id, contexto_id), item_type])
    return [item for item, _ in nearest(items, query_embedding, KNOWLEDGE_LIMITS[item_type])]


def query_extractor(state: BiAgentState, embedder: Embeddings) -> dict[str, str]:
    """Recupera DDLs, regras e exemplos SQL do banco vetorial por tipo."""
    log_node_start("extractor", f"pergunta={state['user_input'][:100]!r}")
    tenant_id = state["tenant_id"]
    contexto_id = state.get("contexto_id")

    has_indexed_knowledge = KnowledgeItem.count(_DO_CONTEXTO, _ids(tenant_id, contexto_id)) > 0

    if not has_indexed_knowledge:
        fallback_context = _fallback_examples_for_contexto(contexto_id)
        log_node_end("extractor", f"{len(fallback_context)} chars de contexto (fallback examples.json)")
        return {"retrieved_schema": fallback_context}

    query_embedding = embedder.embed_query(state["user_input"])

    system_prompt = state.get("system_prompt") or ""
    items_by_type = {}
    for item_type in KNOWLEDGE_LIMITS:
        retrieved = list(_search_knowledge(tenant_id, contexto_id, query_embedding, item_type))
        if item_type in ("ddl", "doc") and system_prompt:
            # Evita duplicar no prompt blocos de esquema/regras que já constam integralmente no system_prompt.
            retrieved = [
                item for item in retrieved
                if not (item.content and item.content.strip() in system_prompt)
            ]
        items_by_type[item_type] = retrieved
    context = "\n\n".join(
        f"### {KNOWLEDGE_LABELS[item_type]}\n"
        + "\n\n".join(item.content for item in items)
        for item_type, items in items_by_type.items()
        if items
    )
    log_kv(
        "bi",
        "Contexto recuperado",
        {KNOWLEDGE_LABELS[item_type]: len(items) for item_type, items in items_by_type.items()},
    )
    log_node_end("extractor", f"{len(context)} chars de contexto")
    return {"retrieved_schema": context}
