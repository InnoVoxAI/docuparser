from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context
from tenants.models import Tenant

from accounting.reports import automation_report


class Command(BaseCommand):
    help = "Taxa de automação da classificação em conta (quanto chegou certo sem o analista)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--tenant", required=True)

    def handle(self, *args, **options) -> None:
        tenant = Tenant.objects.filter(slug=options["tenant"]).first()
        if tenant is None:
            raise CommandError(f"Tenant '{options['tenant']}' não existe.")
        with schema_context(tenant.schema_name):
            r = automation_report()
        self.stdout.write(
            f"Documentos: {r.documents} (com condomínio: {r.with_condominium})"
        )
        self.stdout.write(
            f"Conta sugerida e mantida: {r.automatic} | trocada pelo analista: {r.corrected} | "
            f"escolhida sem sugestão: {r.manual_only} | sem conta: {r.without_account}"
        )
        self.stdout.write(f"Taxa de automação (das que têm conta): {r.rate:.0%}")
