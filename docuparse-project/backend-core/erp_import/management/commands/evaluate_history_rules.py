from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context
from tenants.models import Tenant

from erp_import.credentials import CredentialsError
from erp_import.evaluation import evaluate_holdout
from erp_import.factory import build_superlogica_source
from erp_import.sources.base import SourceError


class Command(BaseCommand):
    help = (
        "Aprende as regras com as despesas antigas e mede o acerto nas mais recentes "
        "(somente leitura; não grava nada)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--tenant", required=True)
        parser.add_argument("--months", type=int, default=24, help="Janela total.")
        parser.add_argument(
            "--test-months",
            type=int,
            default=3,
            help="Fim da janela, usado para testar.",
        )

    def handle(self, *args, **options) -> None:
        tenant = Tenant.objects.filter(slug=options["tenant"]).first()
        if tenant is None:
            raise CommandError(f"Tenant '{options['tenant']}' não existe.")
        today = date.today()
        cutoff = today - timedelta(days=30 * options["test_months"])
        with schema_context(tenant.schema_name):
            try:
                source = build_superlogica_source()
                expenses = source.list_expenses(
                    today - timedelta(days=30 * options["months"]), today
                )
            except (CredentialsError, SourceError) as exc:
                raise CommandError(str(exc)) from None
            report = evaluate_holdout(expenses, source.source_name, cutoff, until=today)

        self.stdout.write(
            f"Aprendeu com {report.train} despesas e testou em {report.test}."
        )
        for label, score in (
            ("por CNPJ/CPF", report.by_tax_id),
            ("por nome", report.by_name),
        ):
            self.stdout.write(
                f"  {label}: {score.total} despesas, sugestão em {score.suggested} "
                f"({score.coverage:.0%}), acerto {score.accuracy:.0%}"
            )
        self.stdout.write(f"  sem chave utilizável: {report.unusable}")
