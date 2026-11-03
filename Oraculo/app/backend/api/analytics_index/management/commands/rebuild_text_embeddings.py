from django.core.management.base import BaseCommand, CommandError

from analytics_index.config import TEXT_EMBEDDING_BATCH_SIZE
from analytics_index.management.commands.sync_text_embeddings import get_embedder, resolve_contexto
from analytics_index.services import rebuild_text_embeddings


class Command(BaseCommand):
    help = "Recria os embeddings de valores das views de um contexto."

    def add_arguments(self, parser):
        parser.add_argument("--contexto", help="Slug do contexto.")
        parser.add_argument("--table", help="View do contexto para recriar.")
        parser.add_argument("--batch-size", type=int, default=TEXT_EMBEDDING_BATCH_SIZE)
        parser.add_argument("--limit", type=int, help="Limita a quantidade de candidatos processados por view.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        contexto = resolve_contexto(options.get("contexto"))
        embedder = None if options["dry_run"] else get_embedder()

        try:
            summary = rebuild_text_embeddings(
                contexto=contexto,
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
