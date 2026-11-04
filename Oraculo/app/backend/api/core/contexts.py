"""
Contextos: carregam o views.json de quem forneceu os dados, validam contra o dados.db,
montam a política de leitura e o prompt do agente, e geram o RAG do contexto.

Pasta de um contexto:
    views.json     obrigatório: {"contexto", "nome", "descricao", "views": [...], "llm_row_limit"}
    rules.md       opcional: regras de negócio e métricas
    examples.json  opcional: [{"question": "...", "sql": "..."}]
"""
import json
from pathlib import Path

from django.db import transaction

from .datastore import ReadPolicy, connect_dados
from .models import Contexto, Tenant

BASE_SQL_RULES = """
You are ORACULO-ESX, an AI assistant specialized in data analysis.

Your task is to generate correct, deterministic SQL queries in SQLite.

Rules:
1. Use ONLY the views listed in ALLOWED VIEWS. Never reference any other table or view.
2. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, PRAGMA, schema prefixes or multiple statements.
3. Column names exactly as listed (lowercase).
4. Use LIMIT n, never TOP.
5. Every non-aggregated selected column must appear in GROUP BY.
6. Percentages must use NULLIF to avoid division by zero.
7. Return a single valid SQL query without comments or explanations.
8. SQLite dialect: no ILIKE (LIKE is already case-insensitive for ASCII), no :: casts (use CAST(x AS TYPE)),
   no EXTRACT/date_trunc (use strftime, e.g. CAST(strftime('%Y', 'now') AS INTEGER)).
9. PLURAL vs SINGULAR LIMIT:
   - Plural questions ("quais", "liste", "mostre", "os N mais", "top N"): ORDER BY metric DESC LIMIT 10 unless the user gives N.
   - Singular questions ("qual o", "o/a com maior/menor", "o principal"): LIMIT 1.
   - Filter questions without ranking: no arbitrary LIMIT; filter with WHERE.
"""


# ── Consulta ────────────────────────────────────────────────────────────────

def get_contexto(contexto_id) -> Contexto | None:
    if not contexto_id:
        return None
    return Contexto.objects.filter(id=contexto_id, is_active=True).first()


def pick_contexto(tenant: Tenant, requested_id=None) -> Contexto | None:
    """Contexto de uma conversa nova: o pedido, ou o único ativo do tenant se houver só um."""
    active = Contexto.objects.filter(tenant=tenant, is_active=True)
    if requested_id:
        return active.filter(id=requested_id).first()
    return active.first() if active.count() == 1 else None


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
    with connect_dados(path=dados_path) as conn:
        rows = conn.execute(f'PRAGMA table_info("{view.replace(chr(34), chr(34) * 2)}")').fetchall()
    return [(row["name"], row["type"] or "") for row in rows]


def visible_columns(contexto: Contexto, view: str, dados_path=None) -> list[tuple[str, str]]:
    sensitive = {column for name, column in contexto.sensitive_columns() if name == view.lower()}
    return [(name, kind) for name, kind in view_columns(view, dados_path) if name.lower() not in sensitive]


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
    return "\n\n".join(parts)


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


@transaction.atomic
def load_context_dir(path: str | Path, tenant: Tenant, dados_path=None) -> tuple[Contexto, list[dict], list[str]]:
    """Cria ou atualiza o Contexto a partir da pasta. Devolve (contexto, exemplos, erros)."""
    folder = Path(path)
    spec = json.loads((folder / "views.json").read_text(encoding="utf-8"))
    rules_file = folder / "rules.md"
    examples_file = folder / "examples.json"
    slug = spec.get("contexto") or folder.name

    contexto, _ = Contexto.objects.update_or_create(
        tenant=tenant,
        slug=slug,
        defaults={
            "name": spec.get("nome") or slug,
            "description": spec.get("descricao", ""),
            "views": spec.get("views", []),
            "rules": rules_file.read_text(encoding="utf-8") if rules_file.exists() else "",
            "llm_row_limit": spec.get("llm_row_limit"),
        },
    )
    examples = json.loads(examples_file.read_text(encoding="utf-8")) if examples_file.exists() else []
    errors = validate_contexto(contexto, dados_path)
    if errors:
        contexto.is_active = False
        contexto.save(update_fields=["is_active"])
    elif not contexto.is_active:
        contexto.is_active = True
        contexto.save(update_fields=["is_active"])
    return contexto, examples, errors


def index_contexto(contexto: Contexto, embedder, examples: list[dict], dados_path=None) -> dict:
    """Refaz o RAG do contexto (esquema, regras, exemplos) e o índice de valores. Usa a chave do usuário."""
    from analytics_index.services import rebuild_text_embeddings
    from knowledge.models import KnowledgeItem

    items = [("ddl", describe_views(contexto, dados_path), {})]
    if contexto.rules:
        items.append(("doc", contexto.rules, {}))
    for example in examples:
        items.append((
            "query_example",
            f"Pergunta: {example['question']}\nSQL: {example['sql']}",
            {"question": example["question"]},
        ))

    with transaction.atomic():
        KnowledgeItem.objects.filter(contexto=contexto).delete()
        for item_type, content, metadata in items:
            KnowledgeItem.objects.create(
                tenant=contexto.tenant,
                contexto=contexto,
                item_type=item_type,
                content=content,
                metadata=metadata,
                embedding=embedder.embed_query(content),
            )

    values = rebuild_text_embeddings(contexto, embedder)
    return {"knowledge_items": len(items), "values": values}
