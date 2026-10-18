from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from documents.models import TimeStampedModel


class ImportBatch(TimeStampedModel):
    """Uma sincronização com a fonte. As propostas dela ficam em `proposals`."""

    class Status(models.TextChoices):
        RUNNING = "running", "Em andamento"
        READY = "ready", "Aguardando decisão"
        ERROR = "error", "Erro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RUNNING
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    error_message = models.CharField(max_length=500, blank=True, default="")
    finished_at = models.DateTimeField(null=True, blank=True)


class ImportProposal(TimeStampedModel):
    """Mudança proposta pela fonte. Nada é aplicado sem decisão de um operador."""

    class EntityType(models.TextChoices):
        CONDOMINIUM = "condominium", "Condomínio"
        CHART = "chart", "Plano de contas"
        ACCOUNT = "account", "Conta"

    class Action(models.TextChoices):
        NEW = "new", "Novo"
        UPDATE = "update", "Atualizar"
        DEACTIVATE = "deactivate", "Desativar"
        CONFLICT = "conflict", "Conflito"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        # Aprovada e resolvida já foram aplicadas ao cadastro.
        APPROVED = "approved", "Aprovada"
        RESOLVED = "resolved", "Conflito resolvido"
        REJECTED = "rejected", "Rejeitada"
        SUPERSEDED = "superseded", "Substituída"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="proposals"
    )
    entity_type = models.CharField(max_length=16, choices=EntityType.choices)
    # Id na fonte; para conta, "<id do plano>/<código>".
    external_id = models.CharField(max_length=128)
    action = models.CharField(max_length=16, choices=Action.choices)
    # Só os campos necessários para aplicar a mudança, nunca o payload bruto.
    data = models.JSONField(default=dict)
    diff = models.JSONField(default=dict, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    # Escolha do operador num conflito.
    resolution = models.JSONField(default=dict, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="import_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["entity_type", "external_id", "status"],
                name="erp_import_proposal_entity_idx",
            ),
        ]
