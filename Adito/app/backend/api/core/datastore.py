"""
Bancos de dados locais do desktop.

- app.db (SQLite): banco operacional do Django (usuários, conversas, dashboards, checkpoints, índices derivados).
- dados.duckdb (DuckDB OLAP): banco analítico com as 6 tabelas fato (`vfact_*_resolved`). Sempre aberto
  em modo somente-leitura (`read_only=True`), com acesso externo bloqueado nativamente (`enable_external_access=False`,
  `lock_configuration=True`) e protegido por `ReadPolicy` quando consultado pelo agente/usuário.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

import duckdb

APP_DIR_NAME = "oraculo-esx"
REPO_APP_DIR = Path(__file__).resolve().parents[3]
DEFAULT_REPO_DUCKDB = REPO_APP_DIR / "data" / "dados.duckdb"

_RE_LEADING_EXPLAIN = re.compile(r"^\s*EXPLAIN\s+", re.IGNORECASE)


def data_dir() -> Path:
    """Pasta de dados do usuário (XDG no Linux, %LOCALAPPDATA% no Windows)."""
    override = os.environ.get("ORACULO_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def app_db_path() -> Path:
    return Path(os.environ.get("ORACULO_APP_DB") or data_dir() / "app.db")


def dados_db_path() -> Path:
    """Retorna o caminho do banco analítico DuckDB (`dados.duckdb`)."""
    env_override = os.environ.get("ORACULO_DADOS_DB")
    if env_override:
        return Path(env_override)
    user_duckdb = data_dir() / "dados.duckdb"
    if user_duckdb.exists():
        return user_duckdb
    if DEFAULT_REPO_DUCKDB.exists():
        return DEFAULT_REPO_DUCKDB
    return user_duckdb


@dataclass(frozen=True)
class ReadPolicy:
    """Política de leitura do banco analítico DuckDB (`dados.duckdb`).

    Garante que o SQL consultado acesse somente as tabelas/views fato expostas
    (`exposed_views`) e nunca projete colunas sensíveis (`sensitive_columns`).
    """

    exposed_views: frozenset[str]
    sensitive_columns: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def validate_query(self, sql: str) -> None:
        from agents.bi_agent.sql_security import validate_read_only_sql

        candidate = _RE_LEADING_EXPLAIN.sub("", sql or "").strip()
        is_valid, error = validate_read_only_sql(
            candidate,
            self.exposed_views,
            dialect="duckdb",
            sensitive_columns=self.sensitive_columns,
        )
        if not is_valid:
            raise PermissionError(error or "Acesso negado pela ReadPolicy do banco analítico.")


class DadosRow:
    """Linha retornada pelo DuckDB compatível com `sqlite3.Row` (`dict(row)`, `row['col']`, `row[0]`)."""

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
    """Wrapper sobre o cursor/conexão do DuckDB que devolve `DadosRow`."""

    def __init__(self, raw_conn: duckdb.DuckDBPyConnection) -> None:
        self._raw = raw_conn
        self.description = raw_conn.description
        self._columns: tuple[str, ...] = (
            tuple(col[0] for col in self.description) if self.description else ()
        )

    def _wrap(self, row: tuple[Any, ...] | None) -> DadosRow | None:
        if row is None:
            return None
        return DadosRow(self._columns, tuple(row))

    def fetchone(self) -> DadosRow | None:
        return self._wrap(self._raw.fetchone())

    def fetchmany(self, size: int = 1) -> list[DadosRow]:
        return [DadosRow(self._columns, tuple(r)) for r in self._raw.fetchmany(size)]

    def fetchall(self) -> list[DadosRow]:
        return [DadosRow(self._columns, tuple(r)) for r in self._raw.fetchall()]

    def __iter__(self) -> Iterator[DadosRow]:
        for r in self._raw.fetchall():
            yield DadosRow(self._columns, tuple(r))


class DadosConnection:
    """Conexão somente-leitura com o `dados.duckdb` que aplica `ReadPolicy` quando fornecida."""

    def __init__(
        self,
        raw_conn: duckdb.DuckDBPyConnection,
        policy: ReadPolicy | None = None,
    ) -> None:
        self._conn = raw_conn
        self._policy = policy

    def execute(self, sql: str, parameters: Sequence[Any] | None = None) -> DadosCursor:
        if self._policy is not None:
            self._policy.validate_query(sql)
        if parameters:
            self._conn.execute(sql, list(parameters))
        else:
            self._conn.execute(sql)
        return DadosCursor(self._conn)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> DadosConnection:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def connect_dados(
    policy: ReadPolicy | None = None,
    path: Path | str | None = None,
) -> DadosConnection:
    """Abre o `dados.duckdb` só para leitura com defesa em profundidade.

    - `read_only=True`: impede modificações nos dados e no esquema.
    - `enable_external_access=False`: bloqueia no próprio DuckDB a leitura de arquivos locais ou URLs.
    - `lock_configuration=True`: bloqueia comandos SQL (`SET`) de reativar configurações.
    - `policy`: quando fornecida, valida via AST SQLGlot tabelas permitidas e colunas sensíveis.
    """
    db_path = Path(path or dados_db_path()).resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"dados.duckdb não encontrado em {db_path}. Gere o banco com Adito/scripts/gerar_duckdb.py antes de consultar."
        )
    raw_conn = duckdb.connect(
        str(db_path),
        read_only=True,
        config={
            "enable_external_access": False,  # banco não lê arquivos nem URLs fora dele
            "lock_configuration": True,       # o SQL não consegue religar a opção
        },
    )
    return DadosConnection(raw_conn=raw_conn, policy=policy)
