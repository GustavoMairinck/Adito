from django.core.management.base import BaseCommand, CommandError
from langchain_mistralai import MistralAIEmbeddings

from analytics_index.config import TEXT_EMBEDDING_BATCH_SIZE
from analytics_index.services import sync_text_embeddings
from core.models import Contexto
from agents.config import MISTRAL_API_KEY, MISTRAL_EMBEDDING_MODEL


def resolve_contexto(slug: str | None) -> Contexto:
    if not slug:
        raise CommandError("Informe --contexto <slug>.")
    contexto = Contexto.objects.filter(slug=slug, is_active=True).first()
    if contexto is None:
        raise CommandError(f"Contexto ativo '{slug}' não encontrado. Carregue com load_context.")
    return contexto


def get_embedder():
    if not MISTRAL_API_KEY:
        raise CommandError("MISTRAL_API_KEY não configurada.")
    return MistralAIEmbeddings(model=MISTRAL_EMBEDDING_MODEL, api_key=MISTRAL_API_KEY)


class Command(BaseCommand):
    help = "Sincroniza incrementalmente os embeddings de valores das views de um contexto."

    def add_arguments(self, parser):
        parser.add_argument("--contexto", help="Slug do contexto.")
        parser.add_argument("--table", help="View do contexto para sincronizar.")
        parser.add_argument("--batch-size", type=int, default=TEXT_EMBEDDING_BATCH_SIZE)
        parser.add_argument("--limit", type=int, help="Limita a quantidade de candidatos processados por view.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        contexto = resolve_contexto(options.get("contexto"))
        embedder = None if options["dry_run"] else get_embedder()

        try:
            summary = sync_text_embeddings(
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
            f"Sync concluído: created={summary['created']} skipped={summary['skipped']} dry_run={summary['dry_run']}"
        ))
