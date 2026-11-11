import os

from django.core.management.base import BaseCommand, CommandError

from core.contexts import index_contexto, load_context_dir
from core.models import Tenant


class Command(BaseCommand):
    help = "Carrega um contexto (views.json, rules.md, examples.json), valida no dados.db e opcionalmente indexa."

    def add_arguments(self, parser):
        parser.add_argument("pasta", help="Pasta do contexto com views.json.")
        parser.add_argument("--index", action="store_true", help="Gera o RAG e o índice de valores (usa a chave da Mistral).")

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(name=os.environ.get("DEFAULT_TENANT_NAME", "padrao"))
        try:
            contexto, examples, errors = load_context_dir(options["pasta"], tenant)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f"  {error}"))
            raise CommandError(f"Contexto '{contexto.slug}' carregado como inativo: corrija os erros acima.")

        self.stdout.write(self.style.SUCCESS(
            f"Contexto '{contexto.slug}' válido: {len(contexto.views)} view(s), {len(examples)} exemplo(s)."
        ))
        if options["index"]:
            from analytics_index.management.commands.sync_text_embeddings import get_embedder

            summary = index_contexto(contexto, get_embedder(), examples)
            self.stdout.write(self.style.SUCCESS(
                f"Indexado: {summary['knowledge_items']} item(ns) de RAG, {summary['values']['created']} valor(es)."
            ))
