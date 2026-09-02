from __future__ import annotations

from typing import Any

from django.db.models import Q

from documents.models import Document
from orchestrator.models import OrchestrationRun, TaskExecution

STEP_ORDER = ["ocr", "extraction", "validation_decision"]
STEP_LABELS = {
    "ocr": "OCR",
    "extraction": "Extração",
    "validation_decision": "Validação",
}
# "register" é a caixa estática (sempre alcançada, nunca tem TaskExecution
# própria) — incluída aqui pro filtro "by stage" poder selecionar documentos
# que ainda não passaram por nenhuma task de verdade.
STAGE_KEYS = ["register", *STEP_ORDER]
# Validação é uma decisão humana (tela de Validação já existente), não uma
# falha transitória pra "tentar de novo" — só ocr/extraction são retryable.
RETRYABLE_STEPS = {"ocr", "extraction"}

# Buckets do filtro "fail | pending | completed" da sidebar — reaproveita a
# mesma noção de "pendente" já usada em _STATUS_LABEL_MAP (views.py), pra não
# ter duas definições divergentes do que conta como "ainda em andamento".
PENDING_DOCUMENT_STATUSES = [
    Document.Status.RECEIVED,
    Document.Status.OCR_COMPLETED,
    Document.Status.EXTRACTION_COMPLETED,
    Document.Status.VALIDATION_PENDING,
]
# "Completed" = a revisão humana terminou (aprovada ou rejeitada) — inclui os
# status pós-aprovação (aprovar já dispara a integração ERP, então o
# documento raramente fica parado em APPROVED por muito tempo; ver
# publish_erp_integration_requested). Um documento rejeitado não está mais
# "em andamento", mesmo sem nenhuma falha de execução (por isso "completed"
# e "fail" não são mutuamente exclusivos: um retry que falhou num doc já
# aprovado ainda conta pra "fail").
COMPLETED_DOCUMENT_STATUSES = [
    Document.Status.APPROVED,
    Document.Status.REJECTED,
    Document.Status.ERP_INTEGRATION_REQUESTED,
    Document.Status.ERP_SENT,
    Document.Status.ERP_FAILED,
]

PROCESS_FILTERS = {"fail", "pending", "completed"}

# --- Status "de negócio" ----------------------------------------------------
# A tela de Visão Geral de Processos é usada por analistas de negócio, não por
# desenvolvedores: em vez de expor os ~11 valores técnicos de Document.Status,
# eles são reduzidos a 4 rótulos que descrevem *onde o processo está parado*.
# "Classificação" acontece DEPOIS da validação humana e segue fora da
# plataforma — por isso não existe um estado "Concluído" aqui.
STATUS_GROUP_LABELS = {
    "erro": "Erro",
    "aguardando_validacao": "Aguardando validação",
    "aguardando_classificacao": "Aguardando classificação",
    "em_fila": "Em Fila",
}
STATUS_GROUP_KEYS = set(STATUS_GROUP_LABELS)

# Estados pós-validação: o documento foi aprovado e agora está em (ou
# aguardando) a etapa de classificação/integração que corre fora daqui.
_CLASSIFICATION_STATUSES = {
    Document.Status.APPROVED,
    Document.Status.ERP_INTEGRATION_REQUESTED,
    Document.Status.ERP_SENT,
    Document.Status.ERP_FAILED,
}


def business_status_group(status: str, has_error: bool) -> str:
    """Reduz Document.Status (+ presença de falha de execução) a uma das 4
    chaves de STATUS_GROUP_LABELS. `has_error` vence tudo: qualquer
    TaskExecution ERROR joga o processo pra "erro" independentemente do
    status."""
    if has_error:
        return "erro"
    if status == Document.Status.VALIDATION_PENDING:
        return "aguardando_validacao"
    if status in _CLASSIFICATION_STATUSES:
        return "aguardando_classificacao"
    # RECEIVED / OCR_* / LAYOUT_CLASSIFIED / EXTRACTION_COMPLETED / REJECTED:
    # ainda não chegou numa etapa que exige ação — segue "na fila".
    return "em_fila"


def business_status_label(status: str, has_error: bool) -> str:
    return STATUS_GROUP_LABELS[business_status_group(status, has_error)]


def document_ids_matching_status_group(document_ids, groups) -> set:
    """IDs (dentre `document_ids`) cujo status de negócio está em `groups`.
    Mesma agregação Python de has_error já usada nos outros filtros — ok na
    escala de uma POC, não pensado pra milhões de documentos."""
    invalid = set(groups) - STATUS_GROUP_KEYS
    if invalid:
        raise ValueError(f"unknown status_group(s): {sorted(invalid)}")
    wanted = set(groups)
    error_ids = document_ids_with_error(document_ids)
    status_by_id = dict(
        Document.objects.filter(id__in=document_ids).values_list("id", "status")
    )
    return {
        document_id
        for document_id in document_ids
        if business_status_group(
            status_by_id.get(document_id, ""), document_id in error_ids
        )
        in wanted
    }


def document_ids_with_error(document_ids) -> set:
    """IDs (dentre `document_ids`) com pelo menos uma TaskExecution ERROR."""
    return set(
        TaskExecution.objects.filter(
            orchestration_run__document_id__in=document_ids,
            status=TaskExecution.Status.ERROR,
        ).values_list("orchestration_run__document_id", flat=True)
    )


def current_stage_by_document(document_ids) -> dict:
    """Última task (por -created_at) de cada documento, ou "register" se
    nenhuma TaskExecution existir ainda pra ele (não começou o pipeline)."""
    tasks = (
        TaskExecution.objects.filter(orchestration_run__document_id__in=document_ids)
        .select_related("orchestration_run")
        .order_by("-created_at")
    )
    stage_by_document: dict = {}
    for task in tasks:
        stage_by_document.setdefault(task.orchestration_run.document_id, task.task_name)
    return {
        document_id: stage_by_document.get(document_id, "register")
        for document_id in document_ids
    }


def document_ids_matching_filter(document_ids, filter_value: str) -> set:
    if filter_value == "fail":
        return document_ids_with_error(document_ids)
    if filter_value == "pending":
        statuses = PENDING_DOCUMENT_STATUSES
    elif filter_value == "completed":
        statuses = COMPLETED_DOCUMENT_STATUSES
    else:
        raise ValueError(f"unknown filter '{filter_value}'")
    return set(
        Document.objects.filter(id__in=document_ids, status__in=statuses).values_list(
            "id", flat=True
        )
    )


def document_ids_matching_stage(document_ids, stage: str) -> set:
    if stage not in STAGE_KEYS:
        raise ValueError(f"unknown stage '{stage}'")
    stage_by_document = current_stage_by_document(document_ids)
    return {
        document_id
        for document_id, current_stage in stage_by_document.items()
        if current_stage == stage
    }


_PAYLOAD_KEYS_HIDDEN_FROM_DASHBOARD = {
    "document_id",  # já é o documento cujo pipeline está sendo olhado
    "validation_decision_id",  # id interno do registro, sem valor pro usuário
}


def _execution_dict(task: TaskExecution) -> dict[str, Any]:
    payload = {
        k: v
        for k, v in task.payload.items()
        if k not in _PAYLOAD_KEYS_HIDDEN_FROM_DASHBOARD
    }
    return {
        "task_id": str(task.task_id),
        "attempt": task.attempt,
        "status": task.status,
        "duration_ms": task.duration_ms,
        "error_type": task.error_type or None,
        "error_message": task.error_message or None,
        "created_at": task.created_at.isoformat(),
        # run vazio ("") = disparo automático (pipeline pós-upload); preenchido
        # = ação humana (validação, ou retry manual pelo dashboard) — ver
        # OrchestrationRun.triggered_by.
        "run_name": task.orchestration_run.name,
        "triggered_by": task.orchestration_run.triggered_by or None,
        # Saída de uma tentativa bem-sucedida (ex.: schema/confiança/campos
        # extraídos, ou decisão+motivo da validação) — já vem redigido por
        # redact_payload() (persistence.py) antes de chegar no banco.
        "payload": payload,
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
        # order_by("task_name", "-created_at") deixa o mais recente primeiro
        # dentro de cada grupo de task_name.
        step_status = step_tasks[0].status if step_tasks else "PENDING"
        # A task "validation_decision" TEM sucesso ao registrar uma rejeição
        # (fez exatamente o que devia) — mas a caixa do diagrama representa o
        # resultado de negócio, não se o mecanismo funcionou. "REJECTED" é um
        # status de step à parte (não reaproveita "ERROR": o rótulo/cor de
        # erro no frontend diz "Falhou", que seria enganoso aqui). Não mexe
        # em `executions[].status` (isso continua refletindo a execução real
        # da task, sempre OK).
        if key == "validation_decision" and document.status == Document.Status.REJECTED:
            step_status = "REJECTED"
        steps.append(
            {
                "key": key,
                "label": STEP_LABELS[key],
                "status": step_status,
                "retryable": key in RETRYABLE_STEPS,
                "executions": [_execution_dict(t) for t in step_tasks],
            }
        )

    # "classification" é a última caixa do diagrama e, como "register", é
    # estática: acontece depois da validação humana e continua fora da
    # plataforma, então não tem TaskExecution própria pra rastrear aqui. O
    # estado sai direto do status do documento.
    if document.status == Document.Status.ERP_FAILED:
        classification_status = "ERROR"
    elif document.status in _CLASSIFICATION_STATUSES:
        classification_status = "OK"
    else:
        classification_status = "PENDING"
    steps.append(
        {
            "key": "classification",
            "label": "Classificação",
            "status": classification_status,
            "retryable": False,
            "executions": [],
        }
    )

    return {
        "document_id": str(document.id),
        "original_filename": document.original_filename,
        "steps": steps,
    }


class RetryAlreadyRunningError(Exception):
    """Já existe uma execução em andamento pra este documento/step."""


def retry_step(document_id, step: str, *, triggered_by: str):
    """Roda de novo, síncrono, o @task correspondente ao step, numa
    orchestration_run própria (`retry_{step}`) marcada com `document_id` —
    assim a nova TaskExecution aparece no histórico daquele step no
    dashboard. Chamar o @task sem nenhuma orchestration_run ativa não é
    seguro com o writer real: o decorator ainda gera um run_id avulso (só o
    writer fake dos testes unitários tolera isso), mas o writer Django faz
    TaskExecution.objects.create(orchestration_run=...) esperando uma
    OrchestrationRun já existente com aquele run_id — por isso todo call
    site real (aqui incluído) sempre abre orchestration_run explicitamente.
    `triggered_by` (username de quem clicou) é obrigatório aqui — ao
    contrário do pipeline automático, um retry manual sempre tem um
    responsável identificável.

    Recusa se já existe uma execução RUNNING pro mesmo documento/step —
    achado real: um front-end/proxy travado numa chamada lenta (extração via
    LLM passa fácil de 30-90s) pode acabar disparando uma nova chamada antes
    da anterior terminar, empilhando execuções concorrentes sem que o
    usuário tenha clicado de novo. Checagem simples de existência, não uma
    trava de banco (select_for_update) — suficiente pra barrar o caso
    patológico, não uma garantia sob concorrência pesada de verdade."""
    if step not in RETRYABLE_STEPS:
        raise ValueError(f"step '{step}' is not retryable")

    already_running = OrchestrationRun.objects.filter(
        document_id=document_id,
        status=OrchestrationRun.Status.RUNNING,
    ).filter(Q(name="document_processing") | Q(name=f"retry_{step}")).exists()
    if already_running:
        raise RetryAlreadyRunningError(
            f"Já existe uma execução de '{STEP_LABELS[step]}' em andamento "
            "para este documento — aguarde ela terminar."
        )

    from docuparse_orchestrator.context import orchestration_run

    from documents.services.ocr_processor import extraction_task, ocr_task

    with orchestration_run(
        f"retry_{step}", document_id=str(document_id), triggered_by=triggered_by
    ):
        if step == "ocr":
            return ocr_task(document_id)
        return extraction_task(document_id)
