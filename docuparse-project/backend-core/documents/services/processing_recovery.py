"""Recuperação de documentos que ficaram parados no processamento em segundo plano.

O processamento roda num pool de threads dentro do processo do core
(`processing_queue.py`). Se a tarefa falha sem registro (ex.: pod reiniciado no
meio do OCR, conexão com o banco morta) o documento fica em RECEIVED e o run do
orquestrador fica RUNNING para sempre: o frontend consulta o status sem fim e o
retry manual do dashboard recusa, achando que ainda há uma execução em andamento.

`sweep_stuck_processing` fecha esses runs como FAILED e tira os documentos de
RECEIVED para OCR_FAILED, de onde podem ser reprocessados. Roda pelo comando
`manage.py sweep_stuck_documents` (CronJob), um schema de tenant por vez.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from orchestrator.models import OrchestrationRun

from documents.models import Document

logger = logging.getLogger(__name__)

STUCK_ERROR_TYPE = "StuckInQueue"


def mark_received_document_failed(document_id, *, error_type: str, error: str) -> bool:
    """Move o documento de RECEIVED para OCR_FAILED, guardando o motivo em
    `metadata.processing_error`. Não mexe em documento que já avançou.
    Devolve True se o documento foi alterado."""
    with transaction.atomic():
        document = (
            Document.objects.select_for_update()
            .filter(id=document_id, status=Document.Status.RECEIVED)
            .first()
        )
        if document is None:
            return False
        document.status = Document.Status.OCR_FAILED
        document.metadata = {
            **(document.metadata or {}),
            "processing_error": {"error_type": error_type, "error": error[:500]},
        }
        document.save(update_fields=["status", "metadata", "updated_at"])
    return True


@dataclass
class SweepResult:
    stale_run_ids: list[str] = field(default_factory=list)
    stuck_document_ids: list[str] = field(default_factory=list)


def sweep_stuck_processing(
    *, older_than: timedelta, dry_run: bool = False, now=None
) -> SweepResult:
    """Varre o schema atual. Considera parado:

    - run RUNNING iniciado antes do corte;
    - documento em RECEIVED sem alteração desde o corte e sem run RUNNING
      recente (um run recente é processamento em andamento, não travado).
    """
    now = now or timezone.now()
    cutoff = now - older_than
    result = SweepResult()

    stale_runs = OrchestrationRun.objects.filter(
        status=OrchestrationRun.Status.RUNNING, started_at__lt=cutoff
    )
    result.stale_run_ids = list(stale_runs.values_list("run_id", flat=True))
    if result.stale_run_ids and not dry_run:
        OrchestrationRun.objects.filter(run_id__in=result.stale_run_ids).update(
            status=OrchestrationRun.Status.FAILED, finished_at=now
        )

    active_document_ids = OrchestrationRun.objects.filter(
        status=OrchestrationRun.Status.RUNNING,
        started_at__gte=cutoff,
        document_id__isnull=False,
    ).values_list("document_id", flat=True)
    candidates = (
        Document.objects.filter(status=Document.Status.RECEIVED, updated_at__lt=cutoff)
        .exclude(id__in=active_document_ids)
        .values_list("id", flat=True)
    )

    minutes = int(older_than.total_seconds() // 60)
    message = (
        f"Sem progresso no processamento há mais de {minutes} min; "
        "marcado como falho pela varredura. Reprocesse o documento."
    )
    for document_id in candidates:
        if dry_run or mark_received_document_failed(
            document_id, error_type=STUCK_ERROR_TYPE, error=message
        ):
            result.stuck_document_ids.append(str(document_id))

    return result
