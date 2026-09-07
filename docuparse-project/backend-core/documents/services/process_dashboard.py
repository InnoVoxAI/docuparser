from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import (
    Avg,
    Case,
    Count,
    DateTimeField,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

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

# --- Ordenação da tabela de Processos ---------------------------------------
# Mesma ordem visual de STATUS_GROUP_ORDER no frontend (types.ts) — não é a
# mesma regra que business_status_group() (aquela decide em Python sobre um
# documento já carregado; esta vira SQL via Case/When pra ordenar no banco
# ANTES de paginar), mas usa as mesmas constantes (_CLASSIFICATION_STATUSES,
# VALIDATION_PENDING) pra não divergir da lógica de negócio.
STATUS_GROUP_RANK = {
    "em_fila": 0,
    "aguardando_validacao": 1,
    "aguardando_classificacao": 2,
    "erro": 3,
}

# Nome do param (`?ordering=`) -> nome do campo/annotation anotado no queryset.
# Espelha os campos que a tabela do frontend já mostra (ProcessSummary), pra
# "ordene pela coluna X" ser literal.
ORDERING_FIELDS = {
    "original_filename": "original_filename",
    "status_label": "_status_rank",
    "last_status_change_at": "_last_status_change_at",
}


def annotate_ordering_fields(queryset):
    """Adiciona ao queryset as colunas calculadas usadas por `apply_ordering`:
    `_last_status_change_at` (mesma regra de `last_status_change_by_document`,
    expressa como subquery pra funcionar corretamente com LIMIT/OFFSET — sem
    isso, ordenar por "Última atualização" exigiria carregar a tabela inteira
    em Python antes de paginar) e `_status_rank` (posição do status "de
    negócio", ver STATUS_GROUP_RANK). Só é chamada quando `?ordering=` pede
    uma dessas duas colunas — `original_filename` ordena direto, sem
    annotation."""
    latest_task_at = (
        TaskExecution.objects.filter(orchestration_run__document_id=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )
    has_error_for_sort = Exists(
        TaskExecution.objects.filter(
            orchestration_run__document_id=OuterRef("pk"),
            status=TaskExecution.Status.ERROR,
        )
    )
    return queryset.annotate(
        _last_status_change_at=Coalesce(
            Subquery(latest_task_at, output_field=DateTimeField()),
            F("received_at"),
            output_field=DateTimeField(),
        ),
        _has_error_for_sort=has_error_for_sort,
    ).annotate(
        _status_rank=Case(
            When(_has_error_for_sort=True, then=Value(STATUS_GROUP_RANK["erro"])),
            When(
                status=Document.Status.VALIDATION_PENDING,
                then=Value(STATUS_GROUP_RANK["aguardando_validacao"]),
            ),
            When(
                status__in=list(_CLASSIFICATION_STATUSES),
                then=Value(STATUS_GROUP_RANK["aguardando_classificacao"]),
            ),
            default=Value(STATUS_GROUP_RANK["em_fila"]),
            output_field=IntegerField(),
        )
    )


def apply_ordering(queryset, ordering_param: str | None):
    """Aplica `?ordering=<campo>` (prefixo `-` = descendente) ao queryset da
    tabela de Processos. `None`/vazio mantém o default (`-received_at`, mais
    recentes primeiro). Levanta `ValueError` se o campo não for um dos
    ORDERING_FIELDS — quem chama decide o 400."""
    if not ordering_param:
        return queryset.order_by("-received_at")

    descending = ordering_param.startswith("-")
    field = ordering_param[1:] if descending else ordering_param
    if field not in ORDERING_FIELDS:
        raise ValueError(field)

    annotated_field = ORDERING_FIELDS[field]
    if annotated_field.startswith("_"):
        queryset = annotate_ordering_fields(queryset)
    ordering = f"-{annotated_field}" if descending else annotated_field
    # Desempate estável por received_at (mais recente primeiro) — várias linhas
    # podem empatar em status_rank/last_status_change_at (ex.: vários "Em Fila").
    return queryset.order_by(ordering, "-received_at")


# Quando um step não tem TaskExecution registrada (pipeline que não passa pelo
# orquestrador da POC, dados legados, reprocessamento fora do fluxo...), o
# `status` do documento ainda diz até onde ele avançou. Sem esse fallback, um
# documento já em VALIDATION_PENDING aparecia com "Em fila / Ingestão" ainda
# pendentes no breakdown, contradizendo o rótulo "Aguardando validação".
_STEPS_DONE_BY_STATUS: dict[str, set[str]] = {
    Document.Status.RECEIVED: set(),
    Document.Status.OCR_FAILED: set(),
    Document.Status.OCR_COMPLETED: {"ocr"},
    Document.Status.LAYOUT_CLASSIFIED: {"ocr"},
    Document.Status.EXTRACTION_COMPLETED: {"ocr", "extraction"},
    Document.Status.VALIDATION_PENDING: {"ocr", "extraction"},
    Document.Status.APPROVED: {"ocr", "extraction", "validation_decision"},
    Document.Status.REJECTED: {"ocr", "extraction"},
    Document.Status.ERP_INTEGRATION_REQUESTED: {
        "ocr",
        "extraction",
        "validation_decision",
    },
    Document.Status.ERP_SENT: {"ocr", "extraction", "validation_decision"},
    Document.Status.ERP_FAILED: {"ocr", "extraction", "validation_decision"},
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


def latest_activity_by_document(document_ids) -> dict:
    """Última TaskExecution (por -created_at) de cada documento — a
    "transição de fase" mais recente detectada pelo pipeline. Base de
    `current_stage_by_document` e `last_status_change_by_document`: uma
    query só, reaproveitada pelas duas leituras (stage e timestamp) pra não
    duplicar o `SELECT` em quem precisa das duas."""
    tasks = (
        TaskExecution.objects.filter(orchestration_run__document_id__in=document_ids)
        .select_related("orchestration_run")
        .order_by("-created_at")
    )
    activity_by_document: dict = {}
    for task in tasks:
        activity_by_document.setdefault(
            task.orchestration_run.document_id, (task.task_name, task.created_at)
        )
    return activity_by_document


def current_stage_by_document(document_ids) -> dict:
    """Nome da etapa (`STAGE_KEYS`) em que cada documento está agora, ou
    "register" se nenhuma TaskExecution existir ainda pra ele (não começou
    o pipeline)."""
    activity_by_document = latest_activity_by_document(document_ids)
    return {
        document_id: activity_by_document.get(document_id, ("register", None))[0]
        for document_id in document_ids
    }


def last_status_change_by_document(documents) -> dict:
    """Quando cada documento entrou na fase em que está agora — o
    `created_at` da TaskExecution mais recente (ela É a transição: cada
    task registrada representa o pipeline avançando o documento pra uma
    nova etapa/status), ou `received_at` pra quem ainda não tem nenhuma
    (ainda "em fila", sem transição registrada). `documents` é um iterável
    de instâncias `Document` (precisa de `.id`/`.received_at` carregados —
    não faz outra query pra buscá-los)."""
    document_ids = [document.id for document in documents]
    activity_by_document = latest_activity_by_document(document_ids)
    result: dict = {}
    for document in documents:
        _stage, changed_at = activity_by_document.get(document.id, (None, None))
        result[document.id] = changed_at or document.received_at
    return result


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
    implied_done = _STEPS_DONE_BY_STATUS.get(document.status, set())
    for key in STEP_ORDER:
        step_tasks = executions_by_step[key]
        # order_by("task_name", "-created_at") deixa o mais recente primeiro
        # dentro de cada grupo de task_name. Sem execução registrada, cai no
        # que o `status` do documento já implica (ver _STEPS_DONE_BY_STATUS).
        if step_tasks:
            step_status = step_tasks[0].status
        elif key in implied_done:
            step_status = "OK"
        else:
            step_status = "PENDING"
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
    # estática (sem TaskExecution própria). A classificação acontece depois da
    # validação e continua FORA da plataforma — daqui nunca dá pra afirmar que
    # ela terminou, então a caixa nunca fica "OK/Concluído": no máximo "em
    # andamento" (o frontend deriva isso de validation == OK). Só ERP_FAILED
    # vira erro explícito.
    if document.status == Document.Status.ERP_FAILED:
        classification_status = "ERROR"
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


# Rótulos amigáveis das etapas do pipeline pra tela de estatísticas (a mesma
# noção de "onde o processo está" da coluna Status, com um pouco mais de
# granularidade). "register" = ainda não começou a ser processado.
STAGE_LABELS = {
    "register": "Em fila",
    "ocr": "Ingestão (OCR)",
    "extraction": "Ingestão (extração)",
    "validation_decision": "Validação",
    "classification": "Classificação",
}
STAGE_KEYS_WITH_CLASSIFICATION = [*STAGE_KEYS, "classification"]


def build_process_stats() -> dict[str, Any]:
    """Agrega números sobre todos os processos pra tela de estatísticas —
    quantos em cada fase, quantos com erro, volume, tempos médios. Agregação
    em Python/ORM sobre toda a base: ok pra POC, não pensado pra milhões de
    documentos (mesma ressalva do dashboard de processos)."""
    documents = list(Document.objects.values_list("id", "status"))
    all_ids = [row[0] for row in documents]
    total = len(documents)

    error_doc_ids = {
        doc_id
        for doc_id in TaskExecution.objects.filter(
            status=TaskExecution.Status.ERROR
        ).values_list("orchestration_run__document_id", flat=True)
        if doc_id is not None
    }

    # --- por status "de negócio" (os 4 rótulos da coluna Status) ---
    by_status = {key: 0 for key in STATUS_GROUP_LABELS}
    for doc_id, status_value in documents:
        by_status[business_status_group(status_value, doc_id in error_doc_ids)] += 1

    # --- por etapa atual do pipeline (mais granular que o status) ---
    # "classification" e "validation_decision" não dependem de existir uma
    # TaskExecution: o `status` já diz que o documento está esperando lá
    # (achado real, via docker: um documento em VALIDATION_PENDING cuja
    # extração rodou mas ninguém decidiu ainda não tem TaskExecution de
    # validation_decision — cair pra "register"/"em fila" via
    # current_stage_by_document estaria errado). Só ocr/extraction seguem o
    # histórico de execução, que é o que faz sentido pra elas (ainda em
    # ingestão de verdade).
    stage_by_document = current_stage_by_document(all_ids)
    by_stage = {key: 0 for key in STAGE_KEYS_WITH_CLASSIFICATION}
    for doc_id, status_value in documents:
        if status_value in _CLASSIFICATION_STATUSES:
            stage = "classification"
        elif status_value == Document.Status.VALIDATION_PENDING:
            stage = "validation_decision"
        else:
            stage = stage_by_document.get(doc_id, "register")
        by_stage[stage] = by_stage.get(stage, 0) + 1

    # --- erros ---
    error_executions = TaskExecution.objects.filter(status=TaskExecution.Status.ERROR)
    errors_by_step = {
        STAGE_LABELS.get(row["task_name"], row["task_name"]): row["n"]
        for row in error_executions.values("task_name").annotate(n=Count("id"))
    }
    errors_by_type = {
        (row["error_type"] or "Desconhecido"): row["n"]
        for row in error_executions.values("error_type").annotate(n=Count("id"))
    }

    # --- resultado da validação humana ---
    approved = Document.objects.filter(
        status__in=[
            Document.Status.APPROVED,
            Document.Status.ERP_INTEGRATION_REQUESTED,
            Document.Status.ERP_SENT,
            Document.Status.ERP_FAILED,
        ]
    ).count()
    rejected = Document.objects.filter(status=Document.Status.REJECTED).count()

    # --- volume por janela de tempo ---
    now = timezone.now()
    volume = {
        "last_24h": Document.objects.filter(
            received_at__gte=now - timedelta(hours=24)
        ).count(),
        "last_7d": Document.objects.filter(
            received_at__gte=now - timedelta(days=7)
        ).count(),
        "last_30d": Document.objects.filter(
            received_at__gte=now - timedelta(days=30)
        ).count(),
    }

    # --- tempo médio por etapa (ms), só tentativas bem-sucedidas ---
    avg_duration_ms = {
        STAGE_LABELS.get(row["task_name"], row["task_name"]): round(row["avg"] or 0)
        for row in TaskExecution.objects.filter(status=TaskExecution.Status.OK)
        .values("task_name")
        .annotate(avg=Avg("duration_ms"))
        if row["avg"]
    }

    # --- retries manuais (execuções disparadas por uma pessoa, fora a
    # decisão de validação em si) ---
    manual_retries = (
        TaskExecution.objects.exclude(orchestration_run__triggered_by="")
        .exclude(orchestration_run__name="document_validation")
        .count()
    )

    return {
        "total": total,
        "by_status": by_status,
        "by_stage": by_stage,
        "errors": {
            "documents_with_error": len(error_doc_ids & set(all_ids)),
            "by_step": errors_by_step,
            "by_type": errors_by_type,
        },
        "validation": {"approved": approved, "rejected": rejected},
        "volume": volume,
        "avg_duration_ms": avg_duration_ms,
        "manual_retries": manual_retries,
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
