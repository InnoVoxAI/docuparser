from __future__ import annotations

import uuid

from django.db import models
from documents.models import TimeStampedModel


class Condominium(TimeStampedModel):
    """Condomínio administrado pelo tenant; aponta para um plano de contas."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, blank=True, default="")
    # Origem do cadastro (ex. "superlogica") e id do condomínio nela.
    external_source = models.CharField(max_length=32, blank=True, default="")
    external_id = models.CharField(max_length=64, blank=True, default="")
    chart_of_accounts = models.ForeignKey(
        "accounting.ChartOfAccounts",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="condominiums",
    )
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
            models.UniqueConstraint(
                fields=["external_source", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_condominium_external_id_per_source",
            ),
        ]
