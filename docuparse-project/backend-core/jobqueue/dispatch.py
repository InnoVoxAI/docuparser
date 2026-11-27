"""O que cada etapa da fila executa (AR-32).

O worker já trocou para o tenant do job antes de chamar `run_step`. As etapas
`ocr` e `extraction` chamam as funções de hoje pelas variantes `*_job_task`
(`max_attempts=1`), dentro do run de orquestração do documento, retomado pelo
`orchestration_run_id` do job. O `@task` nunca levanta: a classe do erro chega
em `TaskResult.error.retryable`.

O `erp_dispatch` chama `consume_erp_integration_requested` como o pool faz
hoje, sem run nem `@task`: o conector já publica `erp.sent`/`erp.failed`, e a
política da etapa é uma tentativa só. Uma exceção ali sobe para o worker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from docuparse_orchestrator._run_context import current_attempt_override
from docuparse_orchestrator.context import orchestration_run

from jobqueue.models import ProcessingJob

if TYPE_CHECKING:
    from jobqueue.worker import ClaimedJob

# Mesmo nome do run aberto pelo pool em memória (processing_queue.py), para o
# dashboard de processos ler os dois modos do mesmo jeito.
DOCUMENT_RUN_NAME = "document_processing"


@dataclass(frozen=True)
class StepResult:
    ok: bool
    retryable: bool = False
    error_type: str = ""
    error_message: str = ""

    @classmethod
    def success(cls) -> StepResult:
        return cls(ok=True)


def run_step(job: ClaimedJob, tenant: Any) -> StepResult:
    from documents.services import ocr_processor

    if job.step == ProcessingJob.Step.OCR:
        return _run_task(
            job, ocr_processor.ocr_job_task, job.document_id, tenant_slug=tenant.slug
        )
    if job.step == ProcessingJob.Step.EXTRACTION:
        return _run_task(job, ocr_processor.extraction_job_task, job.document_id)
    if job.step == ProcessingJob.Step.ERP_DISPATCH:
        from documents.services.event_consumers import (
            consume_erp_integration_requested,
        )

        consume_erp_integration_requested(job.payload)
        return StepResult.success()
    raise ValueError(f"Etapa desconhecida: {job.step!r}")


def _run_task(job: ClaimedJob, task_fn: Any, *args: Any, **kwargs: Any) -> StepResult:
    attempt_token = current_attempt_override.set(job.attempts)
    try:
        with orchestration_run(
            DOCUMENT_RUN_NAME,
            run_id=job.orchestration_run_id,
            resume=True,
            document_id=str(job.document_id),
            triggered_by=job.triggered_by or None,
        ):
            result = task_fn(*args, **kwargs)
    finally:
        current_attempt_override.reset(attempt_token)

    if result.status == "ok":
        return StepResult.success()
    return StepResult(
        ok=False,
        retryable=result.error.retryable,
        error_type=result.error.type,
        error_message=result.error.message,
    )
