from django.core.management.base import BaseCommand, CommandError

from core.services.sales_bootstrap import (
    SalesBootstrapOptions,
    resolve_tenant,
    run_sales_bootstrap,
)


class Command(BaseCommand):
    help = "Aplica schema/dados de vendas ESX e treina knowledge/embeddings ."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="ID, nome ou schema do tenant.")
        parser.add_argument("--tenant-schema", help="Schema analítico do tenant.")
        parser.add_argument("--reset", action="store_true", help="Remove e recarrega tabelas de vendas.")
        parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria executado sem alterar o banco.")
        parser.add_argument("--skip-training", action="store_true", help="Não treina examples/DDL/doc.")
        parser.add_argument("--skip-embeddings", action="store_true", help="Não sincroniza embeddings textuais.")

    def handle(self, *args, **options):
        try:
            tenant = resolve_tenant(options.get("tenant"), options.get("tenant_schema"))
            summary = run_sales_bootstrap(
                SalesBootstrapOptions(
                    tenant=tenant,
                    reset=options["reset"],
                    dry_run=options["dry_run"],
                    run_training=not options["skip_training"],
                    run_embeddings=not options["skip_embeddings"],
                )
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"Tenant: {summary['tenant']['name']} schema={summary['tenant']['schema']}")
        self.stdout.write(f"Schema statements: {summary['schema']['statements']} applied={summary['schema']['applied']}")
        self.stdout.write(f"Insert statements: {summary['data']['insert_statements']} applied={summary['data']['applied']}")
        self.stdout.write(f"Counts: {summary['counts']}")
        self.stdout.write(f"Training: {summary['training']}")
        self.stdout.write(f"Embeddings: applied={summary['embeddings']['applied']}")
        self.stdout.write(self.style.SUCCESS("Bootstrap de vendas concluído."))
