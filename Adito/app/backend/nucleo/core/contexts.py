"""
Contextos: carregam o views.json de quem forneceu os dados, validam contra o dados.db,
montam a política de leitura e o prompt do agente, e geram o RAG do contexto.

Pasta de um contexto:
    views.json     obrigatório: {"contexto", "nome", "descricao", "ativo": true, "views": [...], "llm_row_limit"}
    rules.md       opcional: regras de negócio e métricas
    examples.json  opcional: [{"question": "...", "sql": "..."}]
"""
import json
import shutil
import sqlite3
from pathlib import Path

from . import db
from .datastore import REPO_APP_DIR, ReadPolicy, connect_dados, data_dir
from .db import to_db_id
from .records import Contexto, KnowledgeItem, Tenant
from .schema import CONTEXTOS_REMOVIDOS

BASE_SQL_RULES = """
You are Adito, an AI assistant specialized in academic and institutional data analysis.

Your task is to generate correct, deterministic SQL queries in SQLite 3.

Rules:
1. Use ONLY the tables/views listed in ALLOWED VIEWS. Never reference any other table, view, or external file function.
2. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, DETACH, PRAGMA, SET, schema prefixes or multiple statements.
3. Column names exactly as listed (lowercase). Never select sensitive columns (CPF or email). Prefer listing explicit columns instead of SELECT *.
4. Use LIMIT n, never TOP.
5. Every non-aggregated selected column must appear in GROUP BY.
6. Percentages must use NULLIF to avoid division by zero.
7. Return a single valid SQL query without comments or explanations.
8. SQLite 3 dialect: you MAY use LIKE for case-insensitive and accent-insensitive matching (e.g. campus LIKE '%Vitoria%'), strftime('%Y', col), CAST(x AS INTEGER), COALESCE, COUNT(DISTINCT col), SUM, AVG, ROUND.
9. PLURAL vs SINGULAR LIMIT:
   - Plural questions ("quais", "liste", "mostre", "os N mais", "top N"): ORDER BY metric DESC LIMIT 10 unless the user gives N.
   - Singular questions ("qual o", "o/a com maior/menor", "o principal"): LIMIT 1.
   - Filter questions without ranking: no arbitrary LIMIT; filter with WHERE.
10. Do NOT add extra WHERE filters (such as IS NOT NULL, year, or status) that the user did not request, except when needed for JOIN keys or excluding NULL years in time-series grouping.
11. When the user specifies an explicit tie-breaker (e.g. "desempate pelo nome do campus"), strictly follow that exact column order in ORDER BY.
"""


# ── Consulta ────────────────────────────────────────────────────────────────

def _db_id(value) -> str | None:
    try:
        return to_db_id(value)
    except (ValueError, TypeError, AttributeError):
        return None


def get_contexto(contexto_id) -> Contexto | None:
    if not contexto_id:
        return None
    cid = _db_id(contexto_id)
    return Contexto.first("id = ? AND is_active = 1", [cid]) if cid else None


def active_contextos(tenant_id) -> list[Contexto]:
    return Contexto.select("tenant_id = ? AND is_active = 1", [to_db_id(tenant_id)], order="name")


def pick_contexto(tenant: Tenant, requested_id=None) -> Contexto | None:
    """Contexto de uma conversa nova: o pedido, ou o único ativo do tenant se houver só um."""
    tid = to_db_id(tenant.id)
    if not Contexto.count("tenant_id = ? AND is_active = 1", [tid]):
        sync_default_contexts(tenant)
    if requested_id:
        cid = _db_id(requested_id)
        return Contexto.first("tenant_id = ? AND is_active = 1 AND id = ?", [tid, cid]) if cid else None
    active = Contexto.select("tenant_id = ? AND is_active = 1", [tid], limit=2)
    return active[0] if len(active) == 1 else None


def read_policy_for(contexto: Contexto | str | None) -> ReadPolicy:
    """Sem contexto, nada fica exposto: o agente não lê nada do dados.db."""
    if not isinstance(contexto, Contexto):
        contexto = get_contexto(contexto)
    if contexto is None:
        return ReadPolicy(frozenset())
    return ReadPolicy(frozenset(contexto.view_names()), frozenset(contexto.sensitive_columns()))


def row_limit_for(contexto_id, default: int) -> int:
    contexto = get_contexto(contexto_id)
    return (contexto.llm_row_limit if contexto and contexto.llm_row_limit else default)


def view_columns(view: str, dados_path=None) -> list[tuple[str, str]]:
    safe_view = view.replace('"', '""')
    with connect_dados(path=dados_path) as conn:
        try:
            rows = conn.execute(f'PRAGMA table_info("{safe_view}")').fetchall()
            if rows:
                return [(str(row["name"]), str(row["type"] or "")) for row in rows]
            # Fallback caso PRAGMA não liste descrição
            cur = conn.execute(f'SELECT * FROM "{safe_view}" LIMIT 0')
            return [(desc[0], "") for desc in cur.description] if cur.description else []
        except sqlite3.Error:
            return []


def visible_columns(contexto: Contexto, view: str, dados_path=None) -> list[tuple[str, str]]:
    sensitive = {column for name, column in contexto.sensitive_columns() if name == view.lower()}
    return [
        (name, kind)
        for name, kind in view_columns(view, dados_path)
        if name.lower() not in sensitive and "cpf" not in name.lower() and "email" not in name.lower()
    ]


def describe_views(contexto: Contexto, dados_path=None) -> str:
    """Esquema das views expostas, já sem as colunas sensíveis (vai para o prompt e para o RAG)."""
    blocks = []
    for view in contexto.views:
        columns = ", ".join(
            f"{name} {kind}".strip() for name, kind in visible_columns(contexto, view["name"], dados_path)
        )
        line = f"- {view['name']}({columns})"
        if view.get("description"):
            line += f"\n  {view['description']}"
        blocks.append(line)
    return "\n".join(blocks)


def build_system_prompt(contexto: Contexto | None, dados_path=None) -> str:
    if contexto is None:
        return BASE_SQL_RULES + "\nNo context selected: do not generate SQL; ask the user to choose a context."
    parts = [BASE_SQL_RULES, f"CONTEXT: {contexto.name}"]
    if contexto.description:
        parts.append(contexto.description)
    parts.append("ALLOWED VIEWS (only these, only these columns):\n" + describe_views(contexto, dados_path))
    if contexto.rules:
        parts.append("BUSINESS RULES AND METRICS:\n" + contexto.rules)
    return "\n".join(parts) if len(parts) == 1 else "\n\n".join(parts)


# ── Carga e validação ───────────────────────────────────────────────────────

def validate_contexto(contexto: Contexto, dados_path=None) -> list[str]:
    """Erros que impedem usar o contexto: view inexistente ou coluna declarada que não existe."""
    errors = []
    if not contexto.views:
        return ["views.json sem views."]
    for view in contexto.views:
        name = view.get("name")
        if not name:
            errors.append("View sem 'name' no views.json.")
            continue
        columns = {column.lower() for column, _ in view_columns(name, dados_path)}
        if not columns:
            errors.append(f"View '{name}' não existe no dados.db.")
            continue
        for key in ("sensitive_columns", "embed_columns", "local_search_columns"):
            missing = [column for column in view.get(key, []) if column.lower() not in columns]
            if missing:
                errors.append(f"View '{name}': {key} inexistentes: {', '.join(missing)}.")
        overlap = {c.lower() for c in view.get("embed_columns", [])} & {c.lower() for c in view.get("sensitive_columns", [])}
        if overlap:
            errors.append(f"View '{name}': coluna sensível não pode ser embedada: {', '.join(sorted(overlap))}.")
    return errors


def load_context_dir(path: str | Path, tenant: Tenant, dados_path=None) -> tuple[Contexto, list[dict], list[str]]:
    """Cria ou atualiza o Contexto a partir da pasta. Devolve (contexto, exemplos, erros)."""
    folder = Path(path)
    spec = json.loads((folder / "views.json").read_text(encoding="utf-8"))
    rules_file = folder / "rules.md"
    examples_file = folder / "examples.json"
    slug = spec.get("contexto") or folder.name

    defaults = {
        "name": spec.get("nome") or slug,
        "description": spec.get("descricao", ""),
        "views": spec.get("views", []),
        "rules": rules_file.read_text(encoding="utf-8") if rules_file.exists() else "",
        "llm_row_limit": spec.get("llm_row_limit"),
    }
    with db.transaction():
        contexto = Contexto.first("tenant_id = ? AND slug = ?", [to_db_id(tenant.id), slug])
        if contexto is None:
            contexto = Contexto(tenant_id=tenant.id, slug=slug, **defaults).insert()
        else:
            for key, value in defaults.items():
                setattr(contexto, key, value)
            contexto.update()
        examples = json.loads(examples_file.read_text(encoding="utf-8")) if examples_file.exists() else []

        if spec.get("ativo") is False:
            if contexto.is_active:
                contexto.is_active = False
                contexto.update("is_active")
            return contexto, examples, []

        errors = validate_contexto(contexto, dados_path)
        if errors:
            contexto.is_active = False
            contexto.update("is_active")
        elif not contexto.is_active:
            contexto.is_active = True
            contexto.update("is_active")
    return contexto, examples, errors


def _slug_da_pasta(folder: Path) -> str:
    try:
        spec = json.loads((folder / "views.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return folder.name
    return spec.get("contexto") or folder.name


def _afastar_contextos_removidos(user_contexts: Path) -> None:
    """Move para contexts.removidos/ as pastas de contextos que saíram do produto.

    Sem isso, uma cópia antiga na pasta de dados (o README antigo mandava copiar a demonstração de
    vendas) recriaria o contexto no app.db a cada abertura. Nada é apagado.
    """
    for folder in list(user_contexts.glob("*")):
        if not (folder / "views.json").exists() or _slug_da_pasta(folder) not in CONTEXTOS_REMOVIDOS:
            continue
        destino_base = user_contexts.parent / "contexts.removidos"
        destino_base.mkdir(parents=True, exist_ok=True)
        destino, n = destino_base / folder.name, 1
        while destino.exists():
            destino, n = destino_base / f"{folder.name}-{n}", n + 1
        shutil.move(str(folder), str(destino))


def context_folders() -> list[Path]:
    """Pastas de contexto: as do app (contexts/) mais as da pasta de dados, que têm prioridade
    quando o nome se repete. Contextos removidos do produto ficam de fora (e saem do caminho)."""
    folders: dict[str, Path] = {}
    repo_contexts = REPO_APP_DIR / "contexts"
    if repo_contexts.exists():
        for p in repo_contexts.glob("*"):
            if (p / "views.json").exists():
                folders[p.name] = p
    user_contexts = data_dir() / "contexts"
    if user_contexts.exists():
        _afastar_contextos_removidos(user_contexts)
        for p in user_contexts.glob("*"):
            if (p / "views.json").exists():
                folders[p.name] = p
    return [p for _, p in sorted(folders.items()) if _slug_da_pasta(p) not in CONTEXTOS_REMOVIDOS]


def sync_default_contexts(tenant: Tenant, dados_path=None) -> list[Contexto]:
    """Sincroniza os contextos das pastas do repositório e da pasta do usuário."""
    synced: list[Contexto] = []
    for folder in context_folders():
        try:
            ctx, _, _ = load_context_dir(folder, tenant, dados_path=dados_path)
            synced.append(ctx)
        except Exception:
            continue

    # Valida contextos já salvos no banco para desativar os que não existem mais no dados.db
    for ctx in Contexto.select("tenant_id = ? AND is_active = 1", [to_db_id(tenant.id)]):
        try:
            errors = validate_contexto(ctx, dados_path=dados_path)
        except FileNotFoundError:
            errors = ["dados.db não encontrado."]
        if errors:
            ctx.is_active = False
            ctx.update("is_active")

    return synced


# `metadata.source` dos itens do RAG criados pelo painel admin; o reindex do contexto não os apaga.
ORIGEM_MANUAL = "admin_panel"


def index_contexto(contexto: Contexto, embedder, examples: list[dict], dados_path=None) -> dict:
    """Refaz o RAG do contexto (esquema, regras, exemplos) e o índice de valores. Usa a chave do usuário."""
    from analytics_index.services import update_text_embeddings

    items = [("ddl", describe_views(contexto, dados_path), {})]
    if contexto.rules:
        items.append(("doc", contexto.rules, {}))
    for example in examples:
        items.append((
            "query_example",
            f"Pergunta: {example['question']}\nSQL: {example['sql']}",
            {"question": example["question"]},
        ))

    # Os embeddings (rede) saem antes da transação para não segurar o app.db travado.
    rows = [(item_type, content, metadata, embedder.embed_query(content)) for item_type, content, metadata in items]
    with db.transaction():
        # Os itens que o admin pôs à mão (Novo treinamento, promover consulta) não vêm dos arquivos e ficam.
        db.execute(
            "DELETE FROM knowledge_knowledgeitem WHERE contexto_id = ?"
            " AND COALESCE(json_extract(metadata, '$.source'), '') <> ?",
            [to_db_id(contexto.id), ORIGEM_MANUAL],
        )
        for item_type, content, metadata, embedding in rows:
            KnowledgeItem(
                tenant_id=contexto.tenant_id,
                contexto_id=contexto.id,
                item_type=item_type,
                content=content,
                metadata=metadata,
                embedding=embedding,
            ).insert()

    values = update_text_embeddings(contexto, embedder)
    return {"knowledge_items": len(items), "values": values}
