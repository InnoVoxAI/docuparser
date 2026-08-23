from __future__ import annotations

from typing import Any

from documents.models import Document
from orchestrator.models import TaskExecution

STEP_ORDER = ["ocr", "extraction", "validation_decision"]
STEP_LABELS = {
    "ocr": "OCR",
    "extraction": "Extração",
    "validation_decision": "Validação",
}
# Validação é uma decisão humana (tela de Validação já existente), não uma
# falha transitória pra "tentar de novo" — só ocr/extraction são retryable.
RETRYABLE_STEPS = {"ocr", "extraction"}


def document_ids_with_error(document_ids) -> set:
    """IDs (dentre `document_ids`) com pelo menos uma TaskExecution ERROR."""
    return set(
        TaskExecution.objects.filter(
            orchestration_run__document_id__in=document_ids,
            status=TaskExecution.Status.ERROR,
        ).values_list("orchestration_run__document_id", flat=True)
    )


def _execution_dict(task: TaskExecution) -> dict[str, Any]:
    return {
        "task_id": str(task.task_id),
        "attempt": task.attempt,
        "status": task.status,
        "duration_ms": task.duration_ms,
        "error_type": task.error_type or None,
        "error_message": task.error_message or None,
        "created_at": task.created_at.isoformat(),
    }


def build_pipeline_detail(document: Document) -> dict[str, Any]:
    """Agrupa o histórico de TaskExecution do documento nos "steps" fixos do
    diagrama do dashboard, mais uma caixa estática "register" (o registro do
    documento é síncrono na request — nunca passa por @task, então não tem
    TaskExecution própria). `document_processing` e `document_validation` são
    duas OrchestrationRuns separadas (trade-off documentado em
    docs/orchestrator-poc-vs-camunda.md); esta função já lê pelas duas, já
    que agrupa por document_id, não por run_id."""
    tasks = list(
        TaskExecution.objects.filter(orchestration_run__document_id=document.id)
        .select_related("orchestration_run")
        .order_by("task_name", "-created_at")
    )
    executions_by_step: dict[str, list[TaskExecution]] = {
        key: [] for key in STEP_ORDER
    }
    for task in tasks:
        if task.task_name in executions_by_step:
            executions_by_step[task.task_name].append(task)

    steps: list[dict[str, Any]] = [
        {
            "key": "register",
            "label": "Registro",
            "status": "OK",
            "retryable": False,
            "executions": [],
        }
    ]
    for key in STEP_ORDER:
        step_tasks = executions_by_step[key]
        steps.append(
            {
                "key": key,
                "label": STEP_LABELS[key],
                # order_by("task_name", "-created_at") deixa o mais recente
                # primeiro dentro de cada grupo de task_name.
                "status": step_tasks[0].status if step_tasks else "PENDING",
                "retryable": key in RETRYABLE_STEPS,
                "executions": [_execution_dict(t) for t in step_tasks],
            }
        )

    return {
        "document_id": str(document.id),
        "original_filename": document.original_filename,
        "steps": steps,
    }


def retry_step(document_id, step: str):
    """Roda de novo, síncrono, o @task correspondente ao step, numa
    orchestration_run própria (`retry_{step}`) marcada com `document_id` —
    assim a nova TaskExecution aparece no histórico daquele step no
    dashboard. Chamar o @task sem nenhuma orchestration_run ativa não é
    seguro com o writer real: o decorator ainda gera um run_id avulso (só o
    writer fake dos testes unitários tolera isso), mas o writer Django faz
    TaskExecution.objects.create(orchestration_run=...) esperando uma
    OrchestrationRun já existente com aquele run_id — por isso todo call
    site real (aqui incluído) sempre abre orchestration_run explicitamente."""
    if step not in RETRYABLE_STEPS:
        raise ValueError(f"step '{step}' is not retryable")

    from docuparse_orchestrator.context import orchestration_run

    from documents.services.ocr_processor import extraction_task, ocr_task

    with orchestration_run(f"retry_{step}", document_id=str(document_id)):
        if step == "ocr":
            return ocr_task(document_id)
        return extraction_task(document_id)
