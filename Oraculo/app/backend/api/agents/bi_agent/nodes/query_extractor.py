from typing import Any

from langchain_core.embeddings import Embeddings

from core.rich_logging import log_kv, log_node_end, log_node_start
from core.vectors import nearest
from knowledge.models import KnowledgeItem

from ..config import KNOWLEDGE_LABELS, KNOWLEDGE_LIMITS
from ..state import BiAgentState


def _search_knowledge(tenant_id: str, query_embedding: Any, item_type: str):
    items = KnowledgeItem.objects.filter(
        tenant_id=tenant_id,
        item_type=item_type,
        embedding__isnull=False,
    )
    return [item for item, _ in nearest(items, query_embedding, KNOWLEDGE_LIMITS[item_type])]


def query_extractor(state: BiAgentState, embedder: Embeddings) -> dict[str, str]:
    """Recupera DDLs, regras e exemplos SQL do banco vetorial por tipo."""
    log_node_start("extractor", f"pergunta={state['user_input'][:100]!r}")
    tenant_id = state["tenant_id"]
    query_embedding = embedder.embed_query(state["user_input"])

    items_by_type = {
        item_type: list(_search_knowledge(tenant_id, query_embedding, item_type))
        for item_type in KNOWLEDGE_LIMITS
    }
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
