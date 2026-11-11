"""
Management command: flush_data

Apaga todos os dados operacionais do ORACULO-ESX para validação de um ambiente limpo,
preservando:
  - O superusuário Django (admin) criado pelo create_admin.py

Uso:
    python manage.py flush_data
    python manage.py flush_data --dry-run          # apenas mostra o que seria apagado
    python manage.py flush_data --keep-email=email@exemplo.com  # preserva usuário extra
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "Remove todos os dados operacionais (conversas, mensagens, queries, "
        "usuários não autorizados) preservando o superusuário e os CPFs autorizados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas exibe o que seria apagado, sem modificar o banco.",
        )
        parser.add_argument(
            "--keep-email",
            type=str,
            default=None,
            help="E-mail adicional de usuário a preservar além do superusuário.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        keep_email = options.get("keep_email")

        # Importações dentro do handle para garantir que o Django já iniciou
        from chat.models import Conversation, Message, QueryExecution
        from core.models import User

        # ── Identifica usuários a PRESERVAR ──────────────────────────────────
        preserved_ids = set(
            User.objects.filter(is_superuser=True).values_list("id", flat=True)
        )

        if keep_email:
            preserved_ids.update(
                User.objects.filter(email=keep_email).values_list("id", flat=True)
            )

        users_to_delete = User.objects.exclude(id__in=preserved_ids)
        preserved_users = User.objects.filter(id__in=preserved_ids)

        # ── Conta registros a apagar ──────────────────────────────────────────
        queries_count = QueryExecution.objects.count()
        messages_count = Message.objects.count()
        conversations_count = Conversation.objects.count()
        users_del_count = users_to_delete.count()

        self.stdout.write("\n" + "─" * 60)
        self.stdout.write(self.style.WARNING("  FLUSH DE DADOS DO ORACULO-ESX"))
        self.stdout.write("─" * 60)
        self.stdout.write(f"  Usuários a PRESERVAR ({preserved_users.count()}):")
        for u in preserved_users:
            flag = "[superuser]" if u.is_superuser else "[cpf autorizado]"
            self.stdout.write(f"    ✔  {u.username} <{u.email}> {flag}")

        self.stdout.write("")
        self.stdout.write(f"  Dados a APAGAR:")
        self.stdout.write(f"    • QueryExecution : {queries_count}")
        self.stdout.write(f"    • Message        : {messages_count}")
        self.stdout.write(f"    • Conversation   : {conversations_count}")
        self.stdout.write(f"    • User           : {users_del_count}")
        self.stdout.write("─" * 60 + "\n")

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS("DRY-RUN: nenhuma alteração foi feita.")
            )
            return

        # ── Executa a limpeza dentro de uma transação ─────────────────────────
        with transaction.atomic():
            # QueryExecution e Message têm FK para User/Conversation com CASCADE,
            # mas deletar explicitamente é mais seguro e mostra a ordem correta.
            deleted_qe, _ = QueryExecution.objects.all().delete()
            deleted_msg, _ = Message.objects.all().delete()
            deleted_conv, _ = Conversation.objects.all().delete()
            deleted_users, _ = users_to_delete.delete()

            # Limpa o estado do checkpointer (histórico de conversas do LangGraph)
            self._flush_checkpoints()

        self.stdout.write(
            self.style.SUCCESS(
                f"Dados removidos: {deleted_qe} queries, "
                f"{deleted_msg} mensagens, "
                f"{deleted_conv} conversas, "
                f"{deleted_users} usuários."
            )
        )

    def _flush_checkpoints(self):
        """Remove o estado das conversas do LangGraph (tabelas do AsyncSqliteSaver)."""
        import sqlite3

        from agents.config import CHECKPOINT_DB_PATH

        try:
            with sqlite3.connect(CHECKPOINT_DB_PATH) as conn:
                existing = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
                }
                removed = 0
                for table in ("writes", "checkpoints"):
                    if table in existing:
                        removed += conn.execute(f"DELETE FROM {table}").rowcount
            self.stdout.write(self.style.SUCCESS(f"Checkpoints: {removed} registro(s) removido(s)."))
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(f"Checkpoints: não foi possível limpar — {exc}")
            )
