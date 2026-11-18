"""
app.db sem ORM: conexão sqlite3 por thread, transações e conversão de tipos.

O esquema é o mesmo que o Django criava (core/schema.sql), então instalações antigas
continuam abrindo. Formato gravado, igual ao do Django:
- ids UUID em hex de 32 caracteres (no código e na API, com hífens);
- datas em texto UTC sem fuso ("2026-11-17 12:00:00.123456");
- JSON em texto; booleanos 0/1; vetores em BLOB float32.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from typing import Any, ClassVar

import numpy as np

from .datastore import app_db_path

_local = threading.local()


def connect() -> sqlite3.Connection:
    """Conexão do thread atual (reaberta se o caminho do app.db mudar, como nos testes)."""
    path = str(app_db_path())
    conn = getattr(_local, "conn", None)
    if conn is None or getattr(_local, "path", None) != path:
        conn = sqlite3.connect(path, timeout=20, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=20000")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn, _local.path, _local.depth = conn, path, 0
    return conn


def close() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


@contextmanager
def transaction():
    """BEGIN IMMEDIATE (como o Django configurado); aninhada vira parte da externa."""
    conn = connect()
    if _local.depth:
        _local.depth += 1
        try:
            yield conn
        finally:
            _local.depth -= 1
        return
    conn.execute("BEGIN IMMEDIATE")
    _local.depth = 1
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
    finally:
        _local.depth = 0


def execute(sql: str, params=()) -> sqlite3.Cursor:
    return connect().execute(sql, params)


# ── Conversões ──────────────────────────────────────────────────────────────

def new_id() -> str:
    return str(uuid.uuid4())


def parse_uuid(value) -> uuid.UUID:
    """Aceita com ou sem hífens; ValueError se não for UUID."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def to_db_id(value) -> str | None:
    return None if value in (None, "") else parse_uuid(value).hex


def from_db_id(value) -> str | None:
    return None if value is None else str(uuid.UUID(value))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_db_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return str(value)


def from_db_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)


def api_dt(value: datetime | None) -> str | None:
    """Formato que o DRF devolvia: ISO 8601 em UTC terminado em Z."""
    if value is None:
        return None
    text = value.astimezone(timezone.utc).isoformat()
    return text[:-6] + "Z" if text.endswith("+00:00") else text


def to_blob(vector: Any) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob) -> np.ndarray:
    return np.frombuffer(bytes(blob), dtype=np.float32)


_TO_DB = {
    "id": to_db_id,
    "dt": to_db_dt,
    "json": lambda v: json.dumps(v),
    "bool": lambda v: None if v is None else int(bool(v)),
    "blob": lambda v: None if v is None else (bytes(v) if isinstance(v, (bytes, bytearray, memoryview)) else to_blob(v)),
}
_FROM_DB = {
    "id": from_db_id,
    "dt": from_db_dt,
    "json": lambda v: None if v is None else json.loads(v),
    "bool": lambda v: None if v is None else bool(v),
    "blob": lambda v: None if v is None else from_blob(v),
}


# ── Registros ───────────────────────────────────────────────────────────────

@dataclass
class Record:
    """Linha de uma tabela. Subclasses declaram `table`, `kinds` (coluna → tipo) e os campos."""

    table: ClassVar[str]
    kinds: ClassVar[dict[str, str]] = {}

    @classmethod
    def columns(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    @classmethod
    def from_row(cls, row: sqlite3.Row):
        values = {}
        for name in cls.columns():
            raw = row[name]
            kind = cls.kinds.get(name)
            values[name] = _FROM_DB[kind](raw) if kind else raw
        return cls(**values)

    @classmethod
    def db_value(cls, name: str, value):
        kind = cls.kinds.get(name)
        return _TO_DB[kind](value) if kind else value

    @classmethod
    def select(cls, where: str = "", params=(), order: str = "", limit: int | None = None) -> list:
        sql = f'SELECT {", ".join(cls.columns())} FROM "{cls.table}"'
        if where:
            sql += f" WHERE {where}"
        if order:
            sql += f" ORDER BY {order}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return [cls.from_row(row) for row in execute(sql, params)]

    @classmethod
    def first(cls, where: str = "", params=(), order: str = ""):
        rows = cls.select(where, params, order, limit=1)
        return rows[0] if rows else None

    @classmethod
    def count(cls, where: str = "", params=()) -> int:
        sql = f'SELECT COUNT(*) FROM "{cls.table}"' + (f" WHERE {where}" if where else "")
        return execute(sql, params).fetchone()[0]

    def insert(self):
        now = utcnow()
        for name in ("created_at", "updated_at"):
            if hasattr(self, name) and getattr(self, name) is None:
                setattr(self, name, now)
        if getattr(self, "id", None) is None:
            self.id = new_id()
        names = self.columns()
        execute(
            f'INSERT INTO "{self.table}" ({", ".join(names)}) VALUES ({", ".join("?" * len(names))})',
            [self.db_value(n, getattr(self, n)) for n in names],
        )
        return self

    def update(self, *names: str):
        """Grava os campos pedidos, ou todos. Como o save() do Django: só a gravação completa
        renova `updated_at`; com campos escolhidos, ele só muda se estiver na lista."""
        if not names:
            if hasattr(self, "updated_at"):
                self.updated_at = utcnow()
            names = tuple(n for n in self.columns() if n != "id")
        execute(
            f'UPDATE "{self.table}" SET {", ".join(f"{n} = ?" for n in names)} WHERE id = ?',
            [*(self.db_value(n, getattr(self, n)) for n in names), to_db_id(self.id)],
        )
        return self
