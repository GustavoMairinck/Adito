import uuid

from django.core.management.base import BaseCommand, CommandError
from langchain_mistralai import MistralAIEmbeddings

from analytics_index.config import TEXT_EMBEDDING_BATCH_SIZE
from analytics_index.services import sync_text_embeddings
from core.models import Tenant
from agents.config import MISTRAL_API_KEY, MISTRAL_EMBEDDING_MODEL


def resolve_tenant(tenant_arg: str | None, tenant_schema: str | None):
    if tenant_schema:
        try:
            return Tenant.objects.get(db_schema_name=tenant_schema)
        except Tenant.DoesNotExist as exc:
            raise CommandError(f"Tenant com schema '{tenant_schema}' não encontrado.") from exc

    if not tenant_arg:
        raise CommandError("Informe --tenant ou --tenant-schema.")

    filters = {"name__iexact": tenant_arg}
    try:
        tenant_uuid = uuid.UUID(str(tenant_arg))
        filters = {"id": tenant_uuid}
    except ValueError:
        pass

    matches = Tenant.objects.filter(**filters)
    if not matches.exists():
        raise CommandError(f"Tenant '{tenant_arg}' não encontrado por id ou nome.")
    if matches.count() > 1:
        raise CommandError(f"Tenant '{tenant_arg}' retornou mais de um resultado.")
    return matches.first()


def get_embedder():
    if not MISTRAL_API_KEY:
        raise CommandError("MISTRAL_API_KEY não configurada.")
    return MistralAIEmbeddings(model=MISTRAL_EMBEDDING_MODEL, api_key=MISTRAL_API_KEY)


class Command(BaseCommand):
    help = "Sincroniza incrementalmente embeddings textuais analíticos configurados."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="ID ou nome do tenant.")
        parser.add_argument("--tenant-schema", help="Schema analítico do tenant.")
        parser.add_argument("--table", help="Tabela/view configurada para sincronizar.")
        parser.add_argument("--batch-size", type=int, default=TEXT_EMBEDDING_BATCH_SIZE)
        parser.add_argument("--limit", type=int, help="Limita a quantidade de candidatos processados por tabela.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        tenant = resolve_tenant(options.get("tenant"), options.get("tenant_schema"))
        embedder = None if options["dry_run"] else get_embedder()

        try:
            summary = sync_text_embeddings(
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
            f"Sync concluído: created={summary['created']} skipped={summary['skipped']} dry_run={summary['dry_run']}"
        ))
