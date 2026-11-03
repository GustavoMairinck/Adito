"""
Arquivos SQLite do desktop.

- app.db: banco do Django (usuários, conversas, dashboards, checkpoints, índices derivados).
- dados.db: dados analíticos fornecidos pelo usuário. Sempre aberto só para leitura,
  com PRAGMA query_only e um authorizer que só deixa o SQL de cima ler as views expostas.
"""
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR_NAME = "oraculo-esx"


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
    return Path(os.environ.get("ORACULO_DADOS_DB") or data_dir() / "dados.db")


def _env_set(name: str) -> set[str]:
    return {item.strip().lower() for item in os.environ.get(name, "").split(",") if item.strip()}


@dataclass(frozen=True)
class ReadPolicy:
    """O que o SQL de nível superior pode ler no dados.db.

    Leituras feitas de dentro de uma view são liberadas (a view vem pronta de quem
    forneceu os dados); no nível de cima só as views expostas e colunas não sensíveis.
    """

    exposed_views: frozenset[str]
    sensitive_columns: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def authorize(self, action, arg1, arg2, db_name, inner_view):
        if action in _ALWAYS_ALLOWED:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            if inner_view is not None:
                return sqlite3.SQLITE_OK
            view = (arg1 or "").lower()
            column = (arg2 or "").lower()
            if view in self.exposed_views and (view, column) not in self.sensitive_columns:
                return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY


_ALWAYS_ALLOWED = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_FUNCTION,
    getattr(sqlite3, "SQLITE_RECURSIVE", 33),
}


def default_read_policy() -> ReadPolicy:
    """Política vinda do ambiente até os contextos existirem.

    ORACULO_EXPOSED_VIEWS="v_a,v_b" e ORACULO_SENSITIVE_COLUMNS="v_a.cpf,v_b.email".
    """
    from agents.bi_agent.config import DEFAULT_SOURCE_TABLE

    views = _env_set("ORACULO_EXPOSED_VIEWS") or {DEFAULT_SOURCE_TABLE}
    sensitive = {
        tuple(item.split(".", 1))
        for item in _env_set("ORACULO_SENSITIVE_COLUMNS")
        if "." in item
    }
    return ReadPolicy(frozenset(views), frozenset(sensitive))


def connect_dados(policy: ReadPolicy | None = None, path: Path | str | None = None) -> sqlite3.Connection:
    """Abre o dados.db só para leitura. Sem policy, não instala authorizer (uso interno do app)."""
    db_path = Path(path or dados_db_path()).resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"dados.db não encontrado em {db_path}. Carregue os dados antes de consultar.")
    conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    if policy is not None:
        conn.set_authorizer(policy.authorize)
    return conn
