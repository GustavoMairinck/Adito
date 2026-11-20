#!/usr/bin/env python3
"""Valida Muninn/etl/.env antes de executar alvos autenticados do ETL.

- Faz parsing seguro sem executar shell/source (trata comentários, espaços, aspas e CRLF).
- Suporta validação granular por escopo: 'all', 'src' ou 'sigpesq'.
- Nunca imprime valores de credenciais, senhas ou segredos no terminal.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = ROOT_DIR / "Muninn" / "etl" / ".env"

INFISICAL_REQUIRED = (
    "INFISICAL_CLIENT_ID",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_PROJECT_ID",
)
ENV_REQUIRED_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "src": ("SRC_USER", "SRC_PASSWORD"),
    "sigpesq": ("SIGPESQ_USER", "SIGPESQ_PASSWORD"),
    "all": ("SRC_USER", "SRC_PASSWORD", "SIGPESQ_USER", "SIGPESQ_PASSWORD"),
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


def validar_env(env_file: Path, escopo: str = "all") -> tuple[bool, str]:
    """Retorna (valido, mensagem). Nunca inclui valores de segredos na mensagem."""
    if escopo not in ENV_REQUIRED_BY_SCOPE:
        return False, f"Escopo de validação inválido: '{escopo}'. Use: all, src ou sigpesq."

    if not env_file.is_file():
        return (
            False,
            f"Arquivo de credenciais não encontrado em '{env_file}'.\n"
            "Execute 'make setup-etl' (ou copie Muninn/etl/.env.example para Muninn/etl/.env) "
            "e preencha as credenciais antes de rodar este comando.",
        )

    env_vars = parse_env_file(env_file)
    modo = env_vars.get("MUNINN_CREDENCIAIS", "").strip().lower()

    if modo not in ("infisical", "env"):
        return (
            False,
            f"Variável MUNINN_CREDENCIAIS ausente ou inválida em '{env_file}'.\n"
            "Defina um dos dois modos aceitos no arquivo:\n"
            "  - MUNINN_CREDENCIAIS=infisical (com INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET e INFISICAL_PROJECT_ID)\n"
            "  - MUNINN_CREDENCIAIS=env       (com SRC_USER, SRC_PASSWORD, SIGPESQ_USER e SIGPESQ_PASSWORD)",
        )

    required = INFISICAL_REQUIRED if modo == "infisical" else ENV_REQUIRED_BY_SCOPE[escopo]
    missing = [key for key in required if not env_vars.get(key, "").strip()]
    if missing:
        lista = ", ".join(missing)
        return (
            False,
            f"Credenciais obrigatórias ausentes/vazias em '{env_file}' (modo MUNINN_CREDENCIAIS={modo}):\n"
            f"  Faltando: {lista}\n"
            "Preencha essas variáveis no arquivo .env e execute o comando novamente.",
        )

    return True, f"Credenciais válidas em '{env_file}' (modo={modo}, escopo={escopo})."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida credenciais configuradas em Muninn/etl/.env.")
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
