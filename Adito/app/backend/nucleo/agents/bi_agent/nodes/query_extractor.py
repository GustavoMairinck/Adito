from contextvars import ContextVar
import json
import logging
from typing import Any

from langchain_core.embeddings import Embeddings

from agents.providers import resolve_active_llm_config
from core.contexts import ORIGEM_MANUAL, get_contexto
from core.datastore import REPO_APP_DIR, data_dir
from core.db import to_db_id
from core.records import KnowledgeItem
from core.rich_logging import log_kv, log_node_end, log_node_start, log_warning
from core.vectors import nearest_with_stats, vector_matches_provider

logger = logging.getLogger(__name__)

from ..config import KNOWLEDGE_LABELS, KNOWLEDGE_LIMITS
from ..state import BiAgentState

FALLBACK_MANUAL_LIMIT = 10
FALLBACK_MANUAL_MAX_CHARS = 800


def _fallback_examples_for_contexto(contexto_id: str | None) -> str:
    """Se o RAG vetorial não estiver disponível, carrega os exemplos do examples.json do contexto."""
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


def _manual_knowledge_for_fallback(
    tenant_id: str,
    contexto_id: str | None,
    system_prompt: str = "",
    limit: int = FALLBACK_MANUAL_LIMIT,
    max_chars: int = FALLBACK_MANUAL_MAX_CHARS,
) -> str:
    """Inclui até `limit` itens manuais do app.db no modo fallback textual, respeitando teto de tamanho."""
    try:
        items = KnowledgeItem.select(
            "(contexto_id = ? OR contexto_id IS NULL) AND tenant_id = ? "
            "AND (COALESCE(json_extract(metadata, '$.source'), '') = ? OR contexto_id IS NULL)",
            [*_ids(tenant_id, contexto_id), ORIGEM_MANUAL],
            order="created_at DESC, rowid DESC",
            limit=limit,
        )
    except Exception as exc:
        logger.warning("Falha ao carregar itens manuais para fallback textual: %s", exc)
        return ""

    by_type: dict[str, list[str]] = {}
    for item in items:
        content = (item.content or "").strip()
        if not content:
            continue
        if item.item_type in ("ddl", "doc") and system_prompt and content in system_prompt:
            continue
        by_type.setdefault(item.item_type, []).append(content[:max_chars])

    blocks = []
    for item_type, texts in by_type.items():
        label = KNOWLEDGE_LABELS.get(item_type, item_type)
        blocks.append(f"### {label} (manual)\n" + "\n\n".join(texts))
    return "\n\n".join(blocks)


def _fallback_context(tenant_id: str, contexto_id: str | None, system_prompt: str = "") -> str:
    parts = [
        _fallback_examples_for_contexto(contexto_id),
        _manual_knowledge_for_fallback(tenant_id, contexto_id, system_prompt=system_prompt),
    ]
    return "\n\n".join(part for part in parts if part)


# Itens do contexto da conversa mais os genéricos (sem contexto).
_DO_CONTEXTO = "(contexto_id = ? OR contexto_id IS NULL) AND tenant_id = ? AND embedding IS NOT NULL"


def _ids(tenant_id, contexto_id) -> list:
    try:
        cid = to_db_id(contexto_id)
    except ValueError:
        cid = None
    return [cid, to_db_id(tenant_id)]


_incompatible_hits: ContextVar[list[int] | None] = ContextVar("adito_extractor_incompatible", default=None)


def _search_knowledge(tenant_id: str, contexto_id: str | None, query_embedding: Any, item_type: str):
    items = KnowledgeItem.select(_DO_CONTEXTO + " AND item_type = ?", [*_ids(tenant_id, contexto_id), item_type])
    cfg = resolve_active_llm_config()
    compatible_items = []
    provider_incompatible = 0
    for item in items:
        meta = item.metadata or {}
        if vector_matches_provider(meta.get("embedding_provider"), meta.get("embedding_model"), cfg):
            compatible_items.append(item)
        else:
            provider_incompatible += 1
    matches, dim_incompatible = nearest_with_stats(compatible_items, query_embedding, KNOWLEDGE_LIMITS[item_type])
    total_incompatible = provider_incompatible + dim_incompatible
    tracker = _incompatible_hits.get()
    if tracker is not None and total_incompatible:
        tracker.append(total_incompatible)
    return [item for item, _ in matches]


def query_extractor(state: BiAgentState, embedder: Embeddings | None) -> dict[str, str]:
    """Recupera DDLs, regras e exemplos SQL do banco vetorial ou opera em fallback textual seguro."""
    log_node_start("extractor", f"pergunta={state['user_input'][:100]!r}")
    tenant_id = state["tenant_id"]
    contexto_id = state.get("contexto_id")
    system_prompt = state.get("system_prompt") or ""

    if embedder is None:
        fallback_context = _fallback_context(tenant_id, contexto_id, system_prompt=system_prompt)
        log_node_end("extractor", f"{len(fallback_context)} chars de contexto (fallback sem embeddings)")
        return {"retrieved_schema": fallback_context}

    has_indexed_knowledge = KnowledgeItem.count(_DO_CONTEXTO, _ids(tenant_id, contexto_id)) > 0

    if not has_indexed_knowledge:
        fallback_context = _fallback_context(tenant_id, contexto_id, system_prompt=system_prompt)
        log_node_end("extractor", f"{len(fallback_context)} chars de contexto (fallback examples.json)")
        return {"retrieved_schema": fallback_context}

    try:
        query_embedding = embedder.embed_query(state["user_input"])
    except Exception as exc:
        log_warning("extractor", f"Embedder indisponível ({exc}); usando fallback textual.")
        fallback_context = _fallback_context(tenant_id, contexto_id, system_prompt=system_prompt)
        log_node_end("extractor", f"{len(fallback_context)} chars de contexto (fallback por falha no embedder)")
        return {"retrieved_schema": fallback_context}

    items_by_type = {}
    incompatible_counts: list[int] = []
    token = _incompatible_hits.set(incompatible_counts)
    try:
        for item_type in KNOWLEDGE_LIMITS:
            retrieved = list(_search_knowledge(tenant_id, contexto_id, query_embedding, item_type))
            if item_type in ("ddl", "doc") and system_prompt:
                # Evita duplicar no prompt blocos de esquema/regras que já constam integralmente no system_prompt.
                retrieved = [
                    item for item in retrieved
                    if not (item.content and item.content.strip() in system_prompt)
                ]
            items_by_type[item_type] = retrieved
    finally:
        _incompatible_hits.reset(token)

    incompatible_total = sum(incompatible_counts)
    if incompatible_total > 0:
        log_warning(
            "extractor",
            f"{incompatible_total} vetor(es) com dimensão incompatível ignorado(s); execute 'Wipe & Retrain' na Base de conhecimento.",
        )

    if not any(items_by_type.values()) and incompatible_total > 0:
        fallback_context = _fallback_context(tenant_id, contexto_id, system_prompt=system_prompt)
        log_node_end("extractor", f"{len(fallback_context)} chars de contexto (fallback por vetores incompatíveis)")
        return {"retrieved_schema": fallback_context}

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
