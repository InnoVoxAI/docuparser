"""Marca como falhos os documentos parados no processamento, em todos os tenants.

Feito para rodar periodicamente (CronJob no k3s, ex.: a cada 10 min). Ver
`documents/services/processing_recovery.py` para o critério de "parado".
Idempotente: rodar de novo sem novos travamentos não altera nada.
Sai com código 1 se algum tenant falhar, para o CronJob registrar o erro.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from documents.services.processing_recovery import sweep_stuck_processing

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Fecha runs RUNNING antigos, marca como OCR_FAILED os documentos parados "
        "em RECEIVED e como falha as extrações paradas em 'running', para poderem "
        "ser reprocessados."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--older-than-minutes",
            type=int,
            default=30,
            help="Tempo sem progresso para considerar parado (default: 30).",
        )
        parser.add_argument(
            "--tenant", help="Slug de um tenant. Sem isto, varre todos os ativos."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Só lista o que seria alterado.",
        )

    def handle(self, *args, **options) -> None:
        from tenants.models import Tenant

        if options["older_than_minutes"] < 1:
            raise CommandError("--older-than-minutes precisa ser >= 1.")
        older_than = timedelta(minutes=options["older_than_minutes"])
        dry_run = options["dry_run"]

        tenants = Tenant.objects.exclude(schema_name=get_public_schema_name())
        if options["tenant"]:
            tenants = tenants.filter(slug=options["tenant"])
            if not tenants.exists():
                raise CommandError(f"Tenant '{options['tenant']}' não existe.")
        else:
            tenants = tenants.filter(is_active=True)

        failed_tenants: list[str] = []
        prefix = "[dry-run] " if dry_run else ""
        for tenant in tenants:
            try:
                with schema_context(tenant.schema_name):
                    result = sweep_stuck_processing(
                        older_than=older_than, dry_run=dry_run
                    )
            except Exception:
                logger.exception(
                    "sweep_stuck_documents_failed | tenant=%s", tenant.slug
                )
                failed_tenants.append(tenant.slug)
                continue

            if result.changed:
                logger.warning(
                    "sweep_stuck_documents | tenant=%s | dry_run=%s | stale_runs=%s | stuck_documents=%s | stuck_extractions=%s",
                    tenant.slug,
                    dry_run,
                    result.stale_run_ids,
                    result.stuck_document_ids,
                    result.stuck_extraction_ids,
                )
            self.stdout.write(
                f"{prefix}{tenant.slug}: {len(result.stale_run_ids)} run(s) fechados, "
                f"{len(result.stuck_document_ids)} documento(s) marcados como falhos, "
                f"{len(result.stuck_extraction_ids)} extração(ões) marcadas como falhas"
            )
            for document_id in result.stuck_document_ids:
                self.stdout.write(f"  documento {document_id}")
            for document_id in result.stuck_extraction_ids:
                self.stdout.write(f"  extração {document_id}")

        if failed_tenants:
            raise CommandError(
                f"Varredura falhou nos tenants: {', '.join(failed_tenants)}"
            )
