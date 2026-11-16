import json
from typing import Any

from django.db.models import Q
from langchain_core.embeddings import Embeddings

from core.contexts import get_contexto
from core.datastore import REPO_APP_DIR, data_dir
from core.rich_logging import log_kv, log_node_end, log_node_start
from core.vectors import nearest
from knowledge.models import KnowledgeItem

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


def _search_knowledge(tenant_id: str, contexto_id: str | None, query_embedding: Any, item_type: str):
    # Itens do contexto da conversa mais os genéricos (sem contexto).
    items = KnowledgeItem.objects.filter(
        Q(contexto_id=contexto_id) | Q(contexto__isnull=True),
        tenant_id=tenant_id,
        item_type=item_type,
        embedding__isnull=False,
    )
    return [item for item, _ in nearest(items, query_embedding, KNOWLEDGE_LIMITS[item_type])]


def query_extractor(state: BiAgentState, embedder: Embeddings) -> dict[str, str]:
    """Recupera DDLs, regras e exemplos SQL do banco vetorial por tipo."""
    log_node_start("extractor", f"pergunta={state['user_input'][:100]!r}")
    tenant_id = state["tenant_id"]
    contexto_id = state.get("contexto_id")

    has_indexed_knowledge = KnowledgeItem.objects.filter(
        Q(contexto_id=contexto_id) | Q(contexto__isnull=True),
        tenant_id=tenant_id,
        embedding__isnull=False,
    ).exists()

    if not has_indexed_knowledge:
        fallback_context = _fallback_examples_for_contexto(contexto_id)
        log_node_end("extractor", f"{len(fallback_context)} chars de contexto (fallback examples.json)")
        return {"retrieved_schema": fallback_context}

    query_embedding = embedder.embed_query(state["user_input"])

    items_by_type = {
        item_type: list(_search_knowledge(tenant_id, contexto_id, query_embedding, item_type))
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
