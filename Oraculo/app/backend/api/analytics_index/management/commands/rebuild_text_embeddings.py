from django.core.management.base import BaseCommand, CommandError

from analytics_index.config import TEXT_EMBEDDING_BATCH_SIZE
from analytics_index.management.commands.sync_text_embeddings import get_embedder, resolve_tenant
from analytics_index.services import rebuild_text_embeddings


class Command(BaseCommand):
    help = "Recria embeddings textuais analíticos configurados para um tenant."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="ID ou nome do tenant.")
        parser.add_argument("--tenant-schema", help="Schema analítico do tenant.")
        parser.add_argument("--table", help="Tabela/view configurada para recriar.")
        parser.add_argument("--batch-size", type=int, default=TEXT_EMBEDDING_BATCH_SIZE)
        parser.add_argument("--limit", type=int, help="Limita a quantidade de candidatos processados por tabela.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        tenant = resolve_tenant(options.get("tenant"), options.get("tenant_schema"))
        embedder = None if options["dry_run"] else get_embedder()

        try:
            summary = rebuild_text_embeddings(
                tenant=tenant,
                embedder=embedder,
                table=options.get("table"),
                batch_size=options["batch_size"],
                dry_run=options["dry_run"],
                limit=options.get("limit"),
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        for table, table_summary in summary["tables"].items():
            self.stdout.write(
                f"{table}: found={table_summary['found']} "
                f"pending={table_summary['pending']} "
                f"created={table_summary['created']} skipped={table_summary['skipped']}"
            )
        self.stdout.write(self.style.SUCCESS(
            f"Rebuild concluído: created={summary['created']} skipped={summary['skipped']} dry_run={summary['dry_run']}"
        ))
