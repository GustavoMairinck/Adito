#!/usr/bin/env python3
"""Valida credenciais do ETL antes de executar alvos autenticados.

- Mesma precedência do ETL (`muninn_etl.comum.config`): primeiro `etl/.env`, depois `os.environ`.
- Funciona em CI/containers sem arquivo `.env` desde que as variáveis estejam exportadas no ambiente.
- Aceita os mesmos aliases do ETL (ex.: `SIGPESQ_USER` ou `SIGPESQ_USERNAME`).
- Faz parsing seguro do `.env` sem executar shell/source (trata comentários, espaços, aspas e CRLF).
- Suporta validação granular por escopo: 'all', 'src' ou 'sigpesq'.
- Nunca imprime valores de credenciais, senhas ou segredos no terminal.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = ROOT_DIR / "Muninn" / "etl" / ".env"

INFISICAL_REQUIRED: tuple[tuple[str, ...], ...] = (
    ("INFISICAL_CLIENT_ID",),
    ("INFISICAL_CLIENT_SECRET",),
    ("INFISICAL_PROJECT_ID",),
)
ENV_REQUIRED_BY_SCOPE: dict[str, tuple[tuple[str, ...], ...]] = {
    "src": (("SRC_USER",), ("SRC_PASSWORD",)),
    "sigpesq": (("SIGPESQ_USER", "SIGPESQ_USERNAME"), ("SIGPESQ_PASSWORD",)),
    "all": (
        ("SRC_USER",),
        ("SRC_PASSWORD",),
        ("SIGPESQ_USER", "SIGPESQ_USERNAME"),
        ("SIGPESQ_PASSWORD",),
    ),
}


def parse_env_file(path: Path) -> dict[str, str]:
    """Lê pares CHAVE=VALOR de um arquivo .env de forma segura (sem execução de código)."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip("\r").strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1].strip()
        elif " #" in val:
            val = val.split(" #", 1)[0].strip()
        values[key] = val
    return values


def _resolve_value(key: str, file_vars: Mapping[str, str], environ: Mapping[str, str]) -> str:
    """Mesma precedência de `muninn_etl.comum.config`: primeiro `.env`, depois ambiente."""
    return (file_vars.get(key) or "").strip() or (environ.get(key) or "").strip()


def _format_alias_group(keys: tuple[str, ...]) -> str:
    return keys[0] if len(keys) == 1 else f"{keys[0]} (ou {'/'.join(keys[1:])})"


def validar_env(
    env_file: Path,
    escopo: str = "all",
    environ: Mapping[str, str] | None = None,
) -> tuple[bool, str]:
    """Retorna (valido, mensagem). Nunca inclui valores de segredos na mensagem."""
    if escopo not in ENV_REQUIRED_BY_SCOPE:
        return False, f"Escopo de validação inválido: '{escopo}'. Use: all, src ou sigpesq."

    env_map = os.environ if environ is None else environ
    has_file = env_file.is_file()
    file_vars = parse_env_file(env_file) if has_file else {}

    modo = _resolve_value("MUNINN_CREDENCIAIS", file_vars, env_map).lower()

    if not has_file and not modo:
        return (
            False,
            f"Arquivo de credenciais não encontrado em '{env_file}' e MUNINN_CREDENCIAIS não está definido no ambiente.\n"
            "Execute 'make setup-etl' (ou copie Muninn/etl/.env.example para Muninn/etl/.env) "
            "ou exporte as variáveis de credenciais no ambiente antes de rodar este comando.",
        )

    if modo not in ("infisical", "env"):
        origem = f"'{env_file}' ou no ambiente" if has_file else "no ambiente (ou crie Muninn/etl/.env)"
        return (
            False,
            f"Variável MUNINN_CREDENCIAIS ausente ou inválida em {origem}.\n"
            "Defina um dos dois modos aceitos:\n"
            "  - MUNINN_CREDENCIAIS=infisical (com INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET e INFISICAL_PROJECT_ID)\n"
            "  - MUNINN_CREDENCIAIS=env       (com SRC_USER, SRC_PASSWORD, SIGPESQ_USER/SIGPESQ_USERNAME e SIGPESQ_PASSWORD)",
        )

    required_groups = INFISICAL_REQUIRED if modo == "infisical" else ENV_REQUIRED_BY_SCOPE[escopo]
    missing = [
        _format_alias_group(group)
        for group in required_groups
        if not any(_resolve_value(k, file_vars, env_map) for k in group)
    ]
    if missing:
        lista = ", ".join(missing)
        origem = f"'{env_file}' (ou ambiente)" if has_file else "ambiente"
        return (
            False,
            f"Credenciais obrigatórias ausentes/vazias em {origem} (modo MUNINN_CREDENCIAIS={modo}):\n"
            f"  Faltando: {lista}\n"
            "Preencha essas variáveis no arquivo .env ou exporte-as no ambiente e tente novamente.",
        )

    fonte = str(env_file) if has_file else "ambiente"
    return True, f"Credenciais válidas em {fonte} (modo={modo}, escopo={escopo})."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida credenciais do ETL (Muninn/etl/.env ou ambiente).")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Caminho para o arquivo .env do ETL")
    parser.add_argument(
        "--escopo",
        choices=("all", "src", "sigpesq"),
        default="all",
        help="Escopo de credenciais exigido no modo MUNINN_CREDENCIAIS=env",
    )
    args = parser.parse_args(argv)

    ok, message = validar_env(args.env_file, escopo=args.escopo)
    if not ok:
        print(f"❌ Erro de configuração do ETL:\n{message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
