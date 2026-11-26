"""
Tabelas do app.db como registros simples (substituem os models do Django).

Cascatas e SET NULL que o ORM fazia sozinho estão nas funções de exclusão abaixo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from . import db
from .db import Record, to_db_id


@dataclass
class Tenant(Record):
    table = "core_tenant"
    kinds = {"id": "id", "is_active": "bool", "created_at": "dt", "updated_at": "dt"}

    id: str | None = None
    name: str = ""
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class User(Record):
    table = "core_user"
    kinds = {
        "id": "id", "tenant_id": "id", "is_staff": "bool", "created_at": "dt", "updated_at": "dt",
    }

    id: str | None = None
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    is_staff: bool = False
    tenant_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Contexto(Record):
    """Pacote de views do dados.db que um chat ou widget pode consultar (views.json)."""

    table = "core_contexto"
    kinds = {"id": "id", "tenant_id": "id", "views": "json", "is_active": "bool", "created_at": "dt", "updated_at": "dt"}

    id: str | None = None
    tenant_id: str | None = None
    slug: str = ""
    name: str = ""
    description: str = ""
    views: list = field(default_factory=list)
    rules: str = ""
    llm_row_limit: int | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def view_names(self) -> list[str]:
        return [view["name"].lower() for view in self.views]

    def view_config(self, name: str) -> dict | None:
        return next((view for view in self.views if view["name"].lower() == name.lower()), None)

    def sensitive_columns(self) -> set[tuple[str, str]]:
        return {
            (view["name"].lower(), column.lower())
            for view in self.views
            for column in view.get("sensitive_columns", [])
        }


@dataclass
class Conversation(Record):
    table = "chat_conversation"
    kinds = {
        "id": "id",
        "user_id": "id",
        "tenant_id": "id",
        "contexto_id": "id",
        "is_pinned": "bool",
        "created_at": "dt",
        "updated_at": "dt",
    }

    id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    contexto_id: str | None = None
    title: str = ""
    is_pinned: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Message(Record):
    table = "chat_message"
    kinds = {"id": "id", "conversation_id": "id", "metadata": "json", "created_at": "dt"}

    id: str | None = None
    conversation_id: str | None = None
    role: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class QueryExecution(Record):
    table = "chat_queryexecution"
    kinds = {
        "id": "id", "user_id": "id", "tenant_id": "id", "contexto_id": "id", "message_id": "id",
        "is_valid": "bool", "created_at": "dt",
    }

    id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    contexto_id: str | None = None
    message_id: str | None = None
    question_original: str = ""
    generated_sql: str = ""
    is_valid: bool = False
    error_message: str | None = None
    execution_time_ms: int | None = None
    created_at: datetime | None = None


@dataclass
class Dashboard(Record):
    table = "dashboard_dashboard"
    kinds = {"id": "id", "user_id": "id", "tenant_id": "id", "created_at": "dt", "updated_at": "dt"}

    id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    name: str = ""
    description: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


CHART_TYPES = ("bar", "line", "metric_card", "horizontal_bar", "area", "pie", "table")
WIDGET_MODES = ("static", "dynamic", "auto")


@dataclass
class Widget(Record):
    table = "dashboard_widget"
    kinds = {
        "id": "id", "dashboard_id": "id", "contexto_id": "id",
        "last_executed_at": "dt", "created_at": "dt", "updated_at": "dt",
    }

    id: str | None = None
    dashboard_id: str | None = None
    contexto_id: str | None = None
    title: str = ""
    question_original: str = ""
    sql_validated: str = ""
    chart_type: str = ""
    mode: str = "static"
    cache_ttl_hours: int = 4
    size: str = "medium"
    grid_x: int = 0
    grid_y: int = 0
    grid_w: int = 4
    grid_h: int = 4
    limit_rows: int = 0
    sort_order: str = "none"
    status: str = "OK"
    last_executed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class KnowledgeItem(Record):
    table = "knowledge_knowledgeitem"
    kinds = {"id": "id", "tenant_id": "id", "contexto_id": "id", "metadata": "json", "embedding": "blob",
             "created_at": "dt", "updated_at": "dt"}

    id: str | None = None
    tenant_id: str | None = None
    contexto_id: str | None = None
    item_type: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)
    embedding: Any = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class AnalyticsTextEmbedding(Record):
    table = "analytics_text_embedding"
    kinds = {"id": "id", "tenant_id": "id", "contexto_id": "id", "payload_json": "json", "embedding": "blob",
             "created_at": "dt", "updated_at": "dt"}

    id: str | None = None
    tenant_id: str | None = None
    contexto_id: str | None = None
    source_table: str = ""
    embedding_text: str = ""
    payload_json: dict = field(default_factory=dict)
    value_hash: str = ""
    embedding: Any = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── Usuário local ───────────────────────────────────────────────────────────

LOCAL_USERNAME = "local"


def get_local_user() -> User:
    """Usuário único do desktop (staff) e o tenant fixo."""
    nome = os.environ.get("DEFAULT_TENANT_NAME", "padrao")
    with db.transaction():
        tenant = Tenant.first("name = ?", [nome], order="created_at")
        if tenant is None:
            tenant = Tenant(name=nome).insert()
        user = User.first("username = ?", [LOCAL_USERNAME])
        if user is None:
            user = User(username=LOCAL_USERNAME, tenant_id=tenant.id, is_staff=True).insert()
        elif user.tenant_id is None:
            user.tenant_id = tenant.id
            user.update("tenant_id")
    return user


def tenant_of(user: User) -> Tenant | None:
    return Tenant.first("id = ?", [to_db_id(user.tenant_id)]) if user.tenant_id else None


# ── Exclusões (o que o ORM fazia em cascata) ────────────────────────────────

def delete_conversation(conversation_id: str) -> None:
    """Apaga as mensagens (CASCADE) e solta as auditorias que apontavam para elas (SET NULL)."""
    cid = to_db_id(conversation_id)
    with db.transaction() as conn:
        conn.execute(
            "UPDATE chat_queryexecution SET message_id = NULL "
            "WHERE message_id IN (SELECT id FROM chat_message WHERE conversation_id = ?)", [cid],
        )
        conn.execute("DELETE FROM chat_message WHERE conversation_id = ?", [cid])
        conn.execute("DELETE FROM chat_conversation WHERE id = ?", [cid])


def delete_widget(widget_id: str) -> None:
    db.execute("DELETE FROM dashboard_widget WHERE id = ?", [to_db_id(widget_id)])
