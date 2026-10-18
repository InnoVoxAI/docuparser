from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from documents.models import TimeStampedModel


class ChartOfAccounts(TimeStampedModel):
    """Plano de contas compartilhado: vários condomínios podem apontar para o mesmo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    # Origem do plano (ex. "superlogica") e id dele nela.
    external_source = models.CharField(max_length=32, blank=True, default="")
    external_id = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["external_source", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_chart_of_accounts_external_id_per_source",
            ),
        ]


class LedgerAccount(TimeStampedModel):
    """Conta de um plano de contas. Hierárquica via `parent`; uma conta sem filhas
    é analítica."""

    class Nature(models.TextChoices):
        INSS = "inss", "INSS"
        FGTS = "fgts", "FGTS"
        SERVICO_PESSOA_FISICA = "servico_pessoa_fisica", "Serviço de pessoa física"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chart = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name="accounts",
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
    # caem na conta do plano marcada com a natureza correspondente.
    nature = models.CharField(
        max_length=32, choices=Nature.choices, blank=True, default=""
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chart", "code"],
                name="unique_ledger_account_code_per_chart",
            ),
            models.UniqueConstraint(
                fields=["chart", "nature"],
                condition=~models.Q(nature=""),
                name="unique_ledger_account_nature_per_chart",
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


class DocumentClassification(TimeStampedModel):
    """Conta atual do documento. O histórico fica nos DocumentEvent `document.classified`."""

    class Origin(models.TextChoices):
        AUTOMATIC = "automatic", "Automática"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        "documents.Document", on_delete=models.CASCADE, related_name="classification"
    )
    ledger_account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="classifications"
    )
    origin = models.CharField(max_length=16, choices=Origin.choices)
    rule_id = models.CharField(max_length=64, blank=True, default="")
    reason = models.CharField(max_length=255, blank=True, default="")
    classified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="document_classifications",
    )
