from __future__ import annotations

from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class ProcessingJob(models.Model):
    """Job da fila durável de processamento (fase 2 da revisão de arquitetura).

    Tabela única no schema `public` (app em SHARED_APPS): uma fila global para
    todos os tenants. `document_id` aponta para um documento que fica no schema
    `tenant_schema`, por isso não há FK. O `OrchestrationRun` continua sendo a
    trilha de auditoria; o job guarda o `run_id` dele em `orchestration_run_id`.

    Os valores dos choices são minúsculos porque o worker faz o claim e a
    recuperação por SQL cru (`status = 'queued'`). As CheckConstraints garantem
    no banco o que os choices só garantem no Django.
    """

    class Step(models.TextChoices):
        OCR = "ocr", "OCR"
        EXTRACTION = "extraction", "Extraction"
        ERP_DISPATCH = "erp_dispatch", "ERP dispatch"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    # Um job ativo por (tenant, documento, etapa): é o que dá a idempotência do
    # enqueue (AR-31) e o 409 do retry de etapa.
    ACTIVE_STATUSES = (Status.QUEUED, Status.RUNNING)

    id = models.BigAutoField(primary_key=True)
    # 63 = limite de identificador do Postgres (nome de schema).
    tenant_schema = models.CharField(max_length=63)
    document_id = models.UUIDField()
    step = models.CharField(max_length=16, choices=Step.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )

    attempts = models.PositiveSmallIntegerField(default=0)
    # Sem default de propósito: o enqueue copia o valor de `policy_for(step)`.
    # Um insert que esqueça o campo falha com NOT NULL em vez de assumir um
    # número de tentativas qualquer.
    max_attempts = models.PositiveSmallIntegerField()
    run_after = models.DateTimeField(default=timezone.now)
    # host:pid:thread do worker que fez o claim.
    locked_by = models.CharField(max_length=255, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    last_error_type = models.CharField(max_length=255, blank=True)
    last_error_message = models.TextField(blank=True)
    # `run_id` do docuparse_orchestrator (OrchestrationRun.run_id, no schema do tenant).
    orchestration_run_id = models.CharField(max_length=36, blank=True)
    # Vazio = disparo automático; preenchido (username) = ação humana.
    triggered_by = models.CharField(max_length=255, blank=True)
    # Dados da etapa, por exemplo o evento do ERP ou {"force": true}.
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_schema", "document_id", "step"],
                condition=Q(status__in=["queued", "running"]),
                name="jobqueue_one_active_job_per_step",
            ),
            models.CheckConstraint(
                condition=Q(step__in=["ocr", "extraction", "erp_dispatch"]),
                name="jobqueue_valid_step",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=["queued", "running", "done", "failed", "cancelled"]
                ),
                name="jobqueue_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(attempts__lte=F("max_attempts")),
                name="jobqueue_attempts_within_max",
            ),
        ]
        indexes = [
            # Claim: WHERE status='queued' AND run_after <= now() ORDER BY run_after, id.
            models.Index(
                fields=["run_after", "id"],
                condition=Q(status="queued"),
                name="jobqueue_claim_idx",
            ),
            # Recuperação (AR-34): jobs running com heartbeat velho.
            models.Index(
                fields=["heartbeat_at"],
                condition=Q(status="running"),
                name="jobqueue_recovery_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.step} {self.document_id} [{self.status}] ({self.tenant_schema})"
