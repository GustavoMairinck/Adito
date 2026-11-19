"""Administração: carga dos contextos, status, auditoria de SQL e treino do RAG."""
import logging
import os
import time

from analytics_index.embedder import get_embedder
from core import db
from core.contexts import context_folders, index_contexto, load_context_dir, validate_contexto
from core.datastore import REPO_APP_DIR, app_db_path, connect_dados, dados_db_path, data_dir
from core.db import api_dt, to_db_id
from core.records import Contexto, KnowledgeItem, QueryExecution, User
from core.rich_logging import log_error, log_success

from .core_methods import llm_configured
from .errors import bad_request, forbidden
from .params import Choice, Str, validate
from .registry import rpc
from .session import current

logger = logging.getLogger(__name__)
SEM_PERMISSAO = "You do not have permission to perform this action."


def _staff():
    user, tenant = current()
    if not user.is_staff:
        raise forbidden(SEM_PERMISSAO)
    return user, tenant


@rpc("admin.query_executions")
def query_executions(params):
    """Execuções de SQL gerado pela IA, para auditoria. `is_valid` filtra; `limit` até 200 (padrão 50)."""
    _, tenant = _staff()
    if tenant is None:
        raise bad_request({"message": "Usuário sem tenant."})
    where, values = "tenant_id = ?", [to_db_id(tenant.id)]
    is_valid = params.get("is_valid")
    if is_valid is not None:
        where += " AND is_valid = ?"
        values.append(int(str(is_valid).lower() == "true"))
    try:
        limit = min(int(params.get("limit", 50)), 200)
    except (TypeError, ValueError):
        limit = 50
    rows = QueryExecution.select(where, values, order="created_at DESC, rowid DESC", limit=limit)
    usernames = {u.id: u.username for u in User.select()}
    return [
        {
            "id": q.id,
            "user": usernames.get(q.user_id),
            "question_original": q.question_original,
            "generated_sql": q.generated_sql,
            "is_valid": q.is_valid,
            "error_message": q.error_message,
            "execution_time_ms": q.execution_time_ms,
            "created_at": api_dt(q.created_at),
            "tenant": q.tenant_id,
            "contexto": q.contexto_id,
            "message": q.message_id,
        }
        for q in rows
    ]


def _service(name: str, url: str, check) -> dict:
    t0 = time.monotonic()
    try:
        check()
        return {"name": name, "status": "online", "latency_ms": round((time.monotonic() - t0) * 1000), "url": url}
    except Exception as exc:
        return {"name": name, "status": "offline", "latency_ms": None, "url": url, "error": str(exc)[:120]}


def _check_dados():
    with connect_dados() as conn:
        conn.execute("SELECT 1")


@rpc("admin.system_status")
def system_status(params):
    """Estado dos bancos locais e do RAG."""
    services = [
        _service("app.db", str(app_db_path()), lambda: db.execute("SELECT 1")),
        _service("dados.db", str(dados_db_path()), _check_dados),
    ]

    uptime_seconds = 0.0
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            uptime_seconds = float(f.readline().split()[0])
    except Exception:
        pass
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

    counts = {"ddl": 0, "doc": 0, "query_example": 0}
    vector_count, last_training = 0, None
    try:
        for item_type, total in db.execute(
            "SELECT item_type, COUNT(*) FROM knowledge_knowledgeitem GROUP BY item_type"
        ):
            counts[item_type] = total
        vector_count = db.execute("SELECT COUNT(*) FROM knowledge_knowledgeitem WHERE embedding IS NOT NULL").fetchone()[0]
        # Texto como está no app.db (o front só exibe).
        last_training = db.execute("SELECT MAX(created_at) FROM knowledge_knowledgeitem").fetchone()[0]
    except Exception as exc:
        logger.warning("Erro ao buscar stats do knowledge: %s", exc)

    return {
        "services": services,
        "systemStats": {
            "version": os.environ.get("APP_VERSION", "0.1.0"),
            "uptime": uptime_str,
            "vectorRows": vector_count,
            "trainedDdl": counts["ddl"],
            "trainedDoc": counts["doc"],
            "trainedExamples": counts["query_example"],
            "lastTraining": last_training,
        },
    }


@rpc("admin.bootstrap")
def bootstrap(params):
    """Recarrega e valida os contextos e, com a chave configurada, gera o RAG e o índice de valores."""
    user, tenant = current()
    if not user.is_staff:
        raise forbidden("Apenas administradores podem preparar os dados.")

    # As mesmas pastas da abertura do app: as do app mais as da pasta de dados. Antes, se a pasta
    # de dados tivesse algum contexto, só ela era lida e os contextos do app ficavam de fora.
    folders = context_folders()
    if not folders:
        raise bad_request({"detail": (
            f"Nenhum contexto encontrado em {REPO_APP_DIR / 'contexts'} nem em {data_dir() / 'contexts'}."
        )})

    loaded = []
    for folder in folders:
        try:
            contexto, examples, errors = load_context_dir(folder, tenant)
        except Exception as exc:
            log_error("data_bootstrap", f"Falha ao carregar {folder.name}: {exc}")
            loaded.append({"pasta": folder.name, "ativo": False, "erros": [str(exc)]})
            continue
        item = {"pasta": folder.name, "slug": contexto.slug, "nome": contexto.name, "ativo": contexto.is_active, "erros": errors}
        if contexto.is_active and not errors and llm_configured():
            try:
                summary = index_contexto(contexto, get_embedder(), examples)
                item.update(indexado=True, rag_itens=summary["knowledge_items"], valores=summary["values"]["created"])
            except Exception as exc:
                log_error("data_bootstrap", f"Falha ao indexar {contexto.slug}: {exc}")
                item.update(indexado=False, erros=[f"Indexação falhou: {exc}"])
        else:
            item["indexado"] = False
        loaded.append(item)

    log_success("data_bootstrap", f"{sum(c['ativo'] for c in loaded)}/{len(loaded)} contexto(s) válidos")
    return {"status": "success", "chave_configurada": llm_configured(), "contextos": loaded}


@rpc("admin.contextos")
def contextos(params):
    """Situação de cada contexto no app.db: ativo, tabelas, RAG, valores indexados e erros atuais."""
    user, tenant = _staff()
    if tenant is None:
        return []
    tid = to_db_id(tenant.id)
    out = []
    for ctx in Contexto.select("tenant_id = ?", [tid], order="name"):
        cid = to_db_id(ctx.id)
        try:
            erros = validate_contexto(ctx)
        except FileNotFoundError:
            erros = ["dados.db não encontrado."]
        except Exception as exc:  # o painel mostra o problema em vez de quebrar
            erros = [str(exc)]
        out.append({
            "id": ctx.id,
            "slug": ctx.slug,
            "nome": ctx.name,
            "descricao": ctx.description,
            "ativo": ctx.is_active,
            "tabelas": [view["name"] for view in ctx.views],
            "rag_itens": db.execute("SELECT COUNT(*) FROM knowledge_knowledgeitem WHERE contexto_id = ?", [cid]).fetchone()[0],
            "valores": db.execute("SELECT COUNT(*) FROM analytics_text_embedding WHERE contexto_id = ?", [cid]).fetchone()[0],
            "atualizado_em": api_dt(ctx.updated_at),
            "erros": erros,
        })
    return out


# ── Treino manual do RAG ────────────────────────────────────────────────────

TYPE_TO_ITEM_TYPE = {"ddl": "ddl", "sql": "query_example", "documentation": "doc"}
TRAINING = {
    "type": Choice(required=True, choices=("ddl", "sql", "documentation")),
    "question": Str(),
    "content": Str(required=True, allow_blank=False),
}


def _get_embedder():
    from agents.config import get_embeddings

    return get_embeddings()


def training_json(item: KnowledgeItem) -> dict:
    meta = item.metadata or {}
    public_type = {"query_example": "sql", "doc": "documentation"}.get(item.item_type, item.item_type)
    if item.item_type == "query_example":
        content = meta.get("sql") or item.content.removeprefix("Q: ").split("\nSQL: ", 1)[-1]
    else:
        content = item.content
    return {
        "id": item.id,
        "type": public_type,
        "name": meta.get("name") or meta.get("question") or meta.get("source") or item.content[:60],
        "question": meta.get("question", ""),
        "content": content,
        "metadata": meta,
        "created_at": api_dt(item.created_at),
        "updated_at": api_dt(item.updated_at),
    }


@rpc("admin.trainings.create")
def trainings_create(params):
    _, tenant = _staff()
    if tenant is None:
        raise bad_request({"message": "Usuário sem tenant."})
    data = validate(TRAINING, params)
    if data["type"] == "sql" and not data.get("question"):
        raise bad_request({"question": ["Pergunta é obrigatória para training SQL."]})

    item_type = TYPE_TO_ITEM_TYPE[data["type"]]
    question = data.get("question", "")
    raw_content = data["content"]
    content = f"Q: {question}\nSQL: {raw_content}" if item_type == "query_example" else raw_content
    metadata = {
        "name": question[:60] if item_type == "query_example" else raw_content[:60],
        "source": "admin_panel",
    }
    if item_type == "query_example":
        metadata.update({"question": question, "sql": raw_content})

    try:
        embedding = _get_embedder().embed_query(question if item_type == "query_example" else raw_content)
    except Exception as exc:
        raise bad_request({"message": f"Não foi possível gerar embedding do training: {exc}"}) from None

    item = KnowledgeItem(tenant_id=tenant.id, item_type=item_type, content=content, metadata=metadata, embedding=embedding)
    return training_json(item.insert())
