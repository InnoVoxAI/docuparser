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
    """Manda os documentos de um fornecedor (CNPJ ou CPF) para uma conta do plano.

    Vale para todos os condomínios do plano; com `condominium` preenchido, só para
    aquele (e vence a regra do plano)."""

    class Origin(models.TextChoices):
        MANUAL = "manual", "Manual"
        HISTORY = "history", "Histórico do ERP"
        LEARNED = "learned", "Aprendida com o analista"

    # Regra vinda do histórico ou do analista só pré-preenche a conta com evidência clara.
    # Medido em teste temporal (aprende com o passado, testa nos últimos meses): 3 lançamentos
    # acertam 94% (cobrem 15%); 2 lançamentos acertam 84% (cobrem 22%).
    MIN_HISTORY_EVIDENCE = 3
    MIN_HISTORY_AGREEMENT = 0.9
    # Regra por nome: nome curto demais ("pix", "tarifa") casaria com qualquer documento.
    MIN_NAME_LENGTH = 8
    MAX_NAME_LENGTH = 64

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chart = models.ForeignKey(
        ChartOfAccounts, on_delete=models.PROTECT, related_name="supplier_rules"
    )
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="supplier_rules",
    )
    # Vazio na regra por nome: ela casa pelo nome do fornecedor no texto (`keyword`).
    supplier_tax_id = models.CharField(max_length=14)
    # Trecho que precisa aparecer no documento: separa cobranças diferentes do
    # mesmo fornecedor (ex. mensalidade vs. contribuição assistencial).
    keyword = models.CharField(max_length=64, blank=True, default="")
    ledger_account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="supplier_rules"
    )
    is_active = models.BooleanField(default=True)
    origin = models.CharField(
        max_length=16, choices=Origin.choices, default=Origin.MANUAL
    )
    # Quantas vezes o fornecedor foi para esta conta, de quantas no total (histórico ou analista).
    evidence_count = models.PositiveIntegerField(default=0)
    evidence_total = models.PositiveIntegerField(default=0)
    # Outras contas já usadas pelo fornecedor: [{"ledger_account_id", "count"}].
    alternatives = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "supplier_tax_id", "keyword"],
                condition=models.Q(condominium__isnull=False),
                name="unique_supplier_rule_per_condominium",
            ),
            models.UniqueConstraint(
                fields=["chart", "supplier_tax_id", "keyword"],
                condition=models.Q(condominium__isnull=True),
                name="unique_supplier_rule_per_chart",
            ),
        ]

    @property
    def agreement(self) -> float:
        return self.evidence_count / self.evidence_total if self.evidence_total else 0.0

    @property
    def is_confident(self) -> bool:
        """Só a regra cadastrada à mão vale sempre; histórico e aprendizado precisam de evidência."""
        if self.origin == self.Origin.MANUAL:
            return True
        return (
            self.evidence_total >= self.MIN_HISTORY_EVIDENCE
            and self.agreement >= self.MIN_HISTORY_AGREEMENT
        )


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
