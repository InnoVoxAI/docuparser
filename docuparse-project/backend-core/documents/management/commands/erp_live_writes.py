"""Habilita ou desabilita o envio REAL de despesas ao Superlógica para um tenant.

É o único jeito de ligar `superlogica_live_enabled`: a API de configurações não
altera esse campo. Mesmo habilitado, o envio real só acontece com todas estas
condições juntas: `SUPERLOGICA_LIVE_WRITES=1` no servidor, contrato de escrita
verificado no código e dry-run desligado (ver `erp_export/policy.py`).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import tenant_context
from tenants.models import Tenant

from documents.models import SETTINGS_SINGLETON_ID, IntegrationSettings


class Command(BaseCommand):
    help = (
        "Habilita ou desabilita o envio real de despesas ao Superlógica (por tenant)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--tenant", required=True, help="Slug do tenant.")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--enable", action="store_true")
        group.add_argument("--disable", action="store_true")
        parser.add_argument(
            "--confirm",
            default="",
            help="Para habilitar, repita o slug do tenant para confirmar.",
        )

    def handle(self, *args, **options) -> None:
        slug = options["tenant"]
        tenant = Tenant.objects.filter(slug=slug).first()
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' não encontrado.")
        enable = bool(options["enable"])
        if enable and options["confirm"] != slug:
            raise CommandError(
                "Habilitar o envio real exige --confirm com o mesmo slug do tenant "
                f"(--confirm {slug})."
            )

        with tenant_context(tenant):
            config, _ = IntegrationSettings.objects.get_or_create(
                id=SETTINGS_SINGLETON_ID
            )
            config.superlogica_live_enabled = enable
            config.save(update_fields=["superlogica_live_enabled", "updated_at"])

        if enable:
            self.stdout.write(
                self.style.WARNING(
                    f"Envio real HABILITADO para '{slug}'. Ainda é preciso "
                    "SUPERLOGICA_LIVE_WRITES=1 no servidor, o contrato verificado "
                    "e o dry-run desligado."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Envio real desabilitado para '{slug}'.")
            )
