"""
Ponto de entrada do backend no desktop (é o que o Tauri sobe, e o alvo do empacotamento).

Migra o app.db, garante o usuário local e sobe o daphne só em 127.0.0.1 na porta pedida.
O Tauri passa ORACULO_LOCAL_TOKEN e ORACULO_DATA_DIR no ambiente.
"""
import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend local do Oráculo ESX")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bi_agent_api.settings")
    if not os.environ.get("ORACULO_LOCAL_TOKEN"):
        sys.exit("ORACULO_LOCAL_TOKEN não definido: o backend não atenderia nenhuma requisição.")

    import django

    django.setup()

    from django.core.management import call_command

    from core.local_auth import get_local_user

    call_command("migrate", interactive=False, verbosity=0)
    get_local_user()

    from daphne.cli import CommandLineInterface

    CommandLineInterface().run(["-b", "127.0.0.1", "-p", str(args.port), "bi_agent_api.asgi:application"])


if __name__ == "__main__":
    main()
