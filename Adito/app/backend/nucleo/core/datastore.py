"""
Bancos de dados locais do desktop.

- app.db (SQLite): banco operacional do app (usuários, conversas, dashboards, checkpoints, índices derivados).
- dados.db (SQLite OLTP / 100% Relacional): banco analítico com as 6 views analíticas (`vfact_*_resolved`)
  calculadas dinamicamente sobre as 42 tabelas base em 3FN.
  Sempre aberto em modo somente-leitura (`mode=ro`), com `PRAGMA query_only = ON`, protegido por
  `set_authorizer` em nível de driver de conexão e por `ReadPolicy` (AST sqlglot) para consultas de agentes.
"""
from __future__ import annotations

import atexit
import os
import re
import sqlite3
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

# Mesmo nome da pasta que o Tauri usa (identifier do tauri.conf.json)
APP_DIR_NAME = "br.edu.ifes.leds.adito"
# Pastas antigas (a mais recente primeiro): Muninn e, antes dele, Oraculo-ESX.
# Só servem para migrar os dados para o Adito.
LEGACY_APP_DIR_NAMES = ("br.edu.ifes.leds.muninn", "br.edu.ifes.leds.oraculo-esx")


def _repo_app_dir() -> Path:
    """Pasta `Adito/app` (onde ficam `contexts/` e `data/`).

    Empacotado pelo PyInstaller (`adito-backend`, US-011), os arquivos do app vão para a pasta
    temporária do executável (`sys._MEIPASS`), e não há `data/dados.db` ali: o dados.db vem da
    pasta do usuário (ADR-0007).
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[3]


REPO_APP_DIR = _repo_app_dir()
DEFAULT_REPO_SQLITE = REPO_APP_DIR / "data" / "dados.db"

_RE_LEADING_EXPLAIN = re.compile(r"^\s*EXPLAIN\s+", re.IGNORECASE)


def _migrate_legacy_dir(base: Path) -> None:
    """Move a pasta de dados antiga mais recente para `base` se `base` ainda não existe (mesmo pai)."""
    if base.exists():
        return
    for nome in LEGACY_APP_DIR_NAMES:
        legacy = base.parent / nome
        if legacy.is_dir():
            legacy.rename(base)
            return


def data_dir() -> Path:
    """Pasta de dados do usuário (XDG no Linux, %LOCALAPPDATA% no Windows)."""
    override = os.environ.get("ADITO_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    if not override:
        _migrate_legacy_dir(base)
    base.mkdir(parents=True, exist_ok=True)
    return base


def app_db_path() -> Path:
    return Path(os.environ.get("ADITO_APP_DB") or data_dir() / "app.db")


def dados_db_path() -> Path:
    """Retorna o caminho do banco de dados acadêmicos SQLite (`dados.db`)."""
    env_override = os.environ.get("ADITO_DADOS_DB")
    if env_override:
        return Path(env_override)
    user_db = data_dir() / "dados.db"
    if user_db.exists():
        return user_db
    if DEFAULT_REPO_SQLITE.exists():
        return DEFAULT_REPO_SQLITE
    return user_db


# ── Custom LIKE (sem acento e case-insensitive) ──────────────────────────────
def strip_accents(s: Any) -> str:
    if s is None:
        return ""
    nfd = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


_LIKE_CACHE: dict[str, re.Pattern] = {}


def _like_to_regex(pattern: str) -> re.Pattern:
    parts = []
    for chunk in re.split(r"(%|_)", pattern):
        if chunk == "%":
            parts.append(".*")
        elif chunk == "_":
            parts.append(".")
        else:
            parts.append(re.escape(chunk))
    regex_str = "^" + "".join(parts) + "$"
    return re.compile(regex_str, re.DOTALL)


def custom_like(pattern: Any, value: Any) -> int:
    """Função SQLite customizada LIKE que ignora acentos (Unicode NFD) e maiúsculas/minúsculas."""
    if pattern is None or value is None:
        return 0
    p = strip_accents(pattern)
    v = strip_accents(value)
    rx = _LIKE_CACHE.get(p)
    if rx is None:
        if len(_LIKE_CACHE) > 1000:
            _LIKE_CACHE.clear()
        rx = _LIKE_CACHE[p] = _like_to_regex(p)
    return 1 if rx.match(v) else 0


# ── Transpilação de Queries com sqlglot ─────────────────────────────────────
def transpile_sql(sql: str) -> str:
    """Transpila consultas SQL (ex: ILIKE, ::INTEGER) de DuckDB para dialeto SQLite nativo quando necessário."""
    if not sql or not sql.strip():
        return sql
    upper = sql.upper()
    # Se não contém construções típicas do DuckDB/PostgreSQL, mantém a query nativa do SQLite
    if "ILIKE" not in upper and "::" not in sql and "EXTRACT(" not in upper:
        return sql
    try:
        import sqlglot
        transpiled = sqlglot.transpile(sql, read="duckdb", write="sqlite")[0]
        return transpiled
    except Exception:
        return sql


# ── Autorizador de Segurança em Nível de Driver SQLite ──────────────────────
ALLOWED_AUTHORIZER_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
}

SAFE_READ_PRAGMAS = {
    "table_info",
    "table_xinfo",
    "database_list",
    "foreign_key_check",
    "query_only",
    "user_version",
}


def _authorizer(action: int, arg1: str | None, arg2: str | None, db_name: str | None, trigger_name: str | None) -> int:
    """Garante que a conexão SQLite execute exclusivamente operações de leitura (SELECT/READ)."""
    if action in ALLOWED_AUTHORIZER_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA:
        pragma_name = (arg1 or "").lower()
        if pragma_name in SAFE_READ_PRAGMAS:
            return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


@dataclass(frozen=True)
class ReadPolicy:
    """Política de leitura do banco analítico (`dados.db`).

    Garante que o SQL consultado pelo usuário/agente acesse somente as views
    analíticas expostas (`exposed_views`) e nunca projete colunas sensíveis (`sensitive_columns`).
    """

    exposed_views: frozenset[str]
    sensitive_columns: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def validate_query(self, sql: str) -> None:
        from agents.bi_agent.sql_security import validate_read_only_sql

        candidate = _RE_LEADING_EXPLAIN.sub("", sql or "").strip()
        is_valid, error = validate_read_only_sql(
            candidate,
            self.exposed_views,
            dialect="sqlite",
            sensitive_columns=self.sensitive_columns,
        )
        if not is_valid:
            # Tenta validação no dialeto DuckDB como fallback antes de transpilar
            is_valid_duck, error_duck = validate_read_only_sql(
                candidate,
                self.exposed_views,
                dialect="duckdb",
                sensitive_columns=self.sensitive_columns,
            )
            if not is_valid_duck:
                raise PermissionError(error or error_duck or "Acesso negado pela ReadPolicy do banco analítico.")


class DadosRow:
    """Linha compatível com `sqlite3.Row` (`dict(row)`, `row['col']`, `row[0]`)."""

    __slots__ = ("_columns", "_values", "_map")

    def __init__(self, columns: tuple[str, ...], values: tuple[Any, ...]) -> None:
        self._columns = columns
        self._values = values
        self._map = dict(zip(columns, values))

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._map[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self) -> tuple[str, ...]:
        return self._columns

    def get(self, key: str, default: Any = None) -> Any:
        return self._map.get(key, default)

    def __repr__(self) -> str:
        return f"DadosRow({self._map!r})"


class DadosCursor:
    """Cursor compatível que encapsula resultados do cursor SQLite."""

    def __init__(self, cur: sqlite3.Cursor) -> None:
        self._cur = cur
        self.description = cur.description
        self._columns: tuple[str, ...] = (
            tuple(col[0] for col in self.description) if self.description else ()
        )

    def _wrap(self, row: Any) -> DadosRow | None:
        if row is None:
            return None
        return DadosRow(self._columns, tuple(row))

    def fetchone(self) -> DadosRow | None:
        return self._wrap(self._cur.fetchone())

    def fetchmany(self, size: int = 1) -> list[DadosRow]:
        return [DadosRow(self._columns, tuple(r)) for r in self._cur.fetchmany(size)]

    def fetchall(self) -> list[DadosRow]:
        return [DadosRow(self._columns, tuple(r)) for r in self._cur.fetchall()]

    def __iter__(self) -> Iterator[DadosRow]:
        for r in self._cur.fetchall():
            yield DadosRow(self._columns, tuple(r))


class DadosConnection:
    """Conexão somente-leitura com o `dados.db` que aplica `ReadPolicy` e transpilação."""

    def __init__(
        self,
        raw_conn: sqlite3.Connection,
        policy: ReadPolicy | None = None,
        on_close=None,
    ) -> None:
        self._conn = raw_conn
        self._policy = policy
        self._on_close = on_close

    def execute(self, sql: str, parameters: Sequence[Any] | None = None) -> DadosCursor:
        candidate = _RE_LEADING_EXPLAIN.sub("", sql or "").strip()
        if self._policy is not None:
            self._policy.validate_query(candidate)
        sql_to_run = transpile_sql(sql)
        if parameters:
            cur = self._conn.execute(sql_to_run, list(parameters))
        else:
            cur = self._conn.execute(sql_to_run)
        return DadosCursor(cur)

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = None
        if self._on_close is not None:
            self._on_close()

    def __enter__(self) -> DadosConnection:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def close_dados() -> None:
    """Hook de encerramento."""
    pass


atexit.register(close_dados)


def connect_dados(
    policy: ReadPolicy | None = None,
    path: Path | str | None = None,
) -> DadosConnection:
    """Conexão estritamente somente-leitura com o `dados.db`, com defesa em profundidade.

    - `mode=ro`: impede modificações em nível de driver de sistema de arquivos.
    - `PRAGMA query_only = ON`: impede comandos SQL de escrita no SQLite.
    - `set_authorizer`: autoriza apenas `SELECT`, `READ` e `FUNCTION`, bloqueando `ATTACH`, DML e DDL.
    - `custom_like`: provê busca resiliente a termos acentuados em português.
    - `policy`: valida via AST SQLGlot relações permitidas e colunas sensíveis.
    """
    db_path = Path(path or dados_db_path()).resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"dados.db não encontrado em {db_path}. Popule o banco com python Adito/scripts/popular_banco.py antes de consultar."
        )

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    conn.execute("PRAGMA query_only = ON;")
    conn.create_function("like", 2, custom_like)
    conn.set_authorizer(_authorizer)

    return DadosConnection(raw_conn=conn, policy=policy)
