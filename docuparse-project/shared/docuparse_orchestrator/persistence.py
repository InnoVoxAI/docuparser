from __future__ import annotations

from typing import Any, Protocol

from docuparse_observability.redaction import is_denied
from docuparse_orchestrator.results import TaskResult


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not is_denied(key)}


class TaskExecutionWriter(Protocol):
    def __call__(self, result: TaskResult) -> None: ...


def default_django_writer(result: TaskResult) -> None:
    from orchestrator.models import OrchestrationRun, TaskExecution

    orchestration_run = OrchestrationRun.objects.get(run_id=result.run_id)
    TaskExecution.objects.create(
        orchestration_run=orchestration_run,
        task_id=result.task_id,
        task_name=result.task_name,
        status=TaskExecution.Status.OK
        if result.status == "ok"
        else TaskExecution.Status.ERROR,
        attempt=result.attempt,
        duration_ms=result.duration_ms,
        payload=redact_payload(result.payload),
        error_type=result.error.type if result.error else "",
        error_message=result.error.message if result.error else "",
    )


class OrchestrationRunWriter(Protocol):
    def start(
        self, run_id: str, name: str, *, document_id: str | None = None
    ) -> None: ...

    def finish(self, run_id: str, *, status: str) -> None: ...


class DjangoOrchestrationRunWriter:
    def start(self, run_id: str, name: str, *, document_id: str | None = None) -> None:
        from django.utils import timezone

        from orchestrator.models import OrchestrationRun

        OrchestrationRun.objects.create(
            run_id=run_id,
            name=name,
            status=OrchestrationRun.Status.RUNNING,
            started_at=timezone.now(),
            document_id=document_id,
        )

    def finish(self, run_id: str, *, status: str) -> None:
        from django.utils import timezone

        from orchestrator.models import OrchestrationRun

        OrchestrationRun.objects.filter(run_id=run_id).update(
            status=status, finished_at=timezone.now()
        )


default_django_run_writer = DjangoOrchestrationRunWriter()
