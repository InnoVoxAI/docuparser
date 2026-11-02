from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context
from tenants.models import Tenant

from erp_import.credentials import CredentialsError
from erp_import.factory import build_superlogica_source
from erp_import.history import seed_rules_from_history
from erp_import.sources.base import SourceError


class Command(BaseCommand):
    help = "Aprende regras de fornecedor com as despesas já lançadas no ERP (somente leitura)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--tenant", required=True, help="Slug do tenant.")
        parser.add_argument(
            "--months", type=int, default=24, help="Janela de despesas, em meses."
        )

    def handle(self, *args, **options) -> None:
        tenant = Tenant.objects.filter(slug=options["tenant"]).first()
        if tenant is None:
            raise CommandError(f"Tenant '{options['tenant']}' não existe.")
        today = date.today()
        with schema_context(tenant.schema_name):
            try:
                source = build_superlogica_source()
                summary = seed_rules_from_history(
                    source, today - timedelta(days=30 * options["months"]), today
                )
            except (CredentialsError, SourceError) as exc:
                raise CommandError(str(exc)) from None
        self.stdout.write(
            f"Despesas lidas: {summary.expenses}. Regras criadas: {summary.rules_created}, "
            f"atualizadas: {summary.rules_updated}, manuais preservadas: {summary.skipped_manual}, "
            f"despesas sem plano ou conta importados: {summary.skipped_unmapped}."
        )
