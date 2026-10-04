from __future__ import annotations

import uuid

from django.db import models
from documents.models import TimeStampedModel


class LedgerAccount(TimeStampedModel):
    """Conta do plano de contas de um condomínio. Hierárquica via `parent`;
    uma conta sem filhas é analítica."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="ledger_accounts",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    # Código da conta no ERP, ex. "2.1.02".
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "code"],
                name="unique_ledger_account_code_per_condominium",
            ),
        ]
