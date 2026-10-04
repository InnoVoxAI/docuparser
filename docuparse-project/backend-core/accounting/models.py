from __future__ import annotations

import uuid

from django.db import models
from documents.models import TimeStampedModel


class LedgerAccount(TimeStampedModel):
    """Conta do plano de contas de um condomínio. Hierárquica via `parent`;
    uma conta sem filhas é analítica."""

    class Nature(models.TextChoices):
        INSS = "inss", "INSS"
        FGTS = "fgts", "FGTS"
        SERVICO_PESSOA_FISICA = "servico_pessoa_fisica", "Serviço de pessoa física"

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
    # Documentos que as regras de conteúdo reconhecem (ex. DARF previdenciário)
    # caem na conta do condomínio marcada com a natureza correspondente.
    nature = models.CharField(
        max_length=32, choices=Nature.choices, blank=True, default=""
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "code"],
                name="unique_ledger_account_code_per_condominium",
            ),
            models.UniqueConstraint(
                fields=["condominium", "nature"],
                condition=~models.Q(nature=""),
                name="unique_ledger_account_nature_per_condominium",
            ),
        ]


class SupplierRule(TimeStampedModel):
    """Manda os documentos de um fornecedor (CNPJ ou CPF) para uma conta do condomínio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="supplier_rules",
    )
    supplier_tax_id = models.CharField(max_length=14)
    # Trecho que precisa aparecer no documento: separa cobranças diferentes do
    # mesmo fornecedor (ex. mensalidade vs. contribuição assistencial).
    keyword = models.CharField(max_length=64, blank=True, default="")
    ledger_account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="supplier_rules"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "supplier_tax_id", "keyword"],
                name="unique_supplier_rule_per_condominium",
            ),
        ]
