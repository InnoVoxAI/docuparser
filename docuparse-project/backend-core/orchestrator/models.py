from __future__ import annotations

import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrchestrationRun(TimeStampedModel):
    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run_id = models.CharField(max_length=36, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RUNNING
    )
    # Sem FK pra documents.Document de propósito: orchestrator nunca importa
    # documents (a dependência entre esses apps só existe no sentido
    # contrário). UUIDField simples ainda permite filtrar/indexar por
    # documento pro dashboard de processos.
    document_id = models.UUIDField(null=True, blank=True, db_index=True)
    # Vazio = disparo automático (pipeline pós-upload). Preenchido (username)
    # = ação humana — decisão de validação ou retry manual pelo dashboard.
    triggered_by = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.run_id})"


class TaskExecution(TimeStampedModel):
    class Status(models.TextChoices):
        OK = "OK", "Ok"
        ERROR = "ERROR", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    orchestration_run = models.ForeignKey(
        OrchestrationRun, on_delete=models.CASCADE, related_name="task_executions"
    )
    task_id = models.UUIDField()
    task_name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices)
    attempt = models.PositiveSmallIntegerField(default=1)
    duration_ms = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    error_type = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.task_name}#{self.attempt} ({self.status})"
