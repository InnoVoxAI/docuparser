from __future__ import annotations

import uuid

from django.db import models
from documents.models import TimeStampedModel


class Condominium(TimeStampedModel):
    """Condomínio administrado pelo tenant; dono de um plano de contas."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, blank=True, default="")
    # Id do condomínio no ERP (Superlógica).
    external_id = models.CharField(max_length=64, blank=True, default="")
    # Outros nomes sob os quais o condomínio aparece nos documentos (ex.
    # "EDIFICIO AVIS LIBERTAS"); usados para identificá-lo quando não há CNPJ.
    aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cnpj"],
                condition=~models.Q(cnpj=""),
                name="unique_condominium_cnpj",
            ),
        ]
