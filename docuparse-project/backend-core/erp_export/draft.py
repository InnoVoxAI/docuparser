"""Monta a despesa a partir de um documento aprovado e valida antes de enviar.

Só leitura do banco local: nenhuma rede. O que depende do ERP (fornecedor, despesa já
lançada) é resolvido depois, no conector.

Quem gera a despesa: uma nota fiscal (com o vencimento e as parcelas vindos dos
boletos do processo de pagamento confirmado) ou um boleto avulso. Um boleto que já
pertence a um processo confirmado não gera despesa própria, para não lançar duas vezes.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from condominiums.tax_ids import is_valid_tax_id, normalize_tax_id
from django.core.exceptions import ObjectDoesNotExist
from documents.models import Document, PaymentProcess
from documents.services.payment_matching import (
    BOLETO_AMOUNT_FIELDS,
    INVOICE_AMOUNT_FIELDS,
    document_fields,
    document_kind,
    parse_amount,
)

from erp_export.errors import DraftInvalid, ExportError

ERP_SOURCE = "superlogica"
_ONE_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Installment:
    amount: Decimal
    due_date: date


@dataclass(frozen=True)
class ExpenseDraft:
    document_id: str
    kind: str
    condominium_external_id: str
    condominium_name: str
    chart_external_id: str
    account_code: str
    account_name: str
    supplier_tax_id: str
    supplier_name: str
    amount: Decimal
    installments: list[Installment]
    issue_date: date | None = None
    competence: str = ""
    document_number: str = ""
    description: str = ""
    due_dates: list[date] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "due_dates", [i.due_date for i in self.installments])

    def summary(self) -> dict[str, Any]:
        """O que a tela mostra para o analista confirmar: sem tokens nem payload do ERP."""
        return {
            "condominium": self.condominium_name,
            "supplier": self.supplier_name,
            "supplier_tax_id": self.supplier_tax_id,
            "account": f"{self.account_code} {self.account_name}".strip(),
            "amount": f"{self.amount:.2f}",
            "installments": [
                {"due_date": i.due_date.isoformat(), "amount": f"{i.amount:.2f}"}
                for i in self.installments
            ],
        }

    def fingerprint(self) -> str:
        """Muda quando algo que vai ao ERP muda (documento corrigido depois do envio)."""
        canonical = json.dumps(
            {
                "document": self.document_id,
                "condominium": self.condominium_external_id,
                "account": self.account_code,
                "supplier": self.supplier_tax_id,
                "amount": f"{self.amount:.2f}",
                "installments": [
                    [i.due_date.isoformat(), f"{i.amount:.2f}"]
                    for i in self.installments
                ],
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


def parse_date(value: Any) -> date | None:
    """Data extraída: ISO (2026-07-10) ou brasileira (10/07/2026)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    br = re.match(r"^(\d{2})/(\d{2})/(\d{4})", text)
    try:
        if iso:
            return date(int(iso[1]), int(iso[2]), int(iso[3]))
        if br:
            return date(int(br[3]), int(br[2]), int(br[1]))
    except ValueError:
        return None
    return None


def _first_amount(fields: dict[str, Any], names: tuple[str, ...]) -> Decimal | None:
    for name in names:
        amount = parse_amount(fields.get(name))
        if amount is not None and amount > 0:
            return amount
    return None


def _text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _check_condominium(
    document: Document, errors: list[ExportError]
) -> tuple[str, str]:
    condominium = document.condominium
    if condominium is None:
        errors.append(
            ExportError(
                "condominium_missing",
                "O condomínio do documento não foi identificado.",
            )
        )
        return "", ""
    if condominium.external_source != ERP_SOURCE or not condominium.external_id:
        errors.append(
            ExportError(
                "condominium_not_linked",
                f"O condomínio {condominium.name} não está ligado ao Superlógica. "
                "Importe os cadastros do Superlógica e confirme a ligação.",
            )
        )
        return "", condominium.name
    return condominium.external_id, condominium.name


def _check_account(
    document: Document, errors: list[ExportError]
) -> tuple[str, str, str]:
    try:
        classification = document.classification
    except ObjectDoesNotExist:
        errors.append(
            ExportError(
                "account_missing", "O documento ainda não tem conta classificada."
            )
        )
        return "", "", ""
    account = classification.ledger_account
    condominium = document.condominium
    if (
        condominium is not None
        and condominium.chart_of_accounts_id
        and account.chart_id != condominium.chart_of_accounts_id
    ):
        errors.append(
            ExportError(
                "account_outside_chart",
                f"A conta {account.code} não pertence ao plano de contas do condomínio.",
            )
        )
    chart = account.chart
    if not chart.external_id:
        errors.append(
            ExportError(
                "account_not_linked",
                f"O plano de contas da conta {account.code} não está ligado ao Superlógica.",
            )
        )
    return chart.external_id, account.code, account.name


def _supplier(
    fields: dict[str, Any], kind: str, errors: list[ExportError]
) -> tuple[str, str]:
    if kind == "invoice":
        raw = fields.get("cnpj_fornecedor") or fields.get("cpf_fornecedor")
        name = _text(fields.get("fornecedor_nome"))
    else:
        raw = fields.get("cnpj_cpf_beneficiario")
        name = _text(fields.get("beneficiario_nome"))
    tax_id = normalize_tax_id(_text(raw))
    if not is_valid_tax_id(tax_id):
        errors.append(
            ExportError(
                "supplier_tax_id_invalid",
                "O CNPJ ou CPF do fornecedor está ausente ou é inválido.",
            )
        )
        return "", name
    return tax_id, name


def _boleto_installment(
    boleto: Document, errors: list[ExportError]
) -> Installment | None:
    fields = document_fields(boleto)
    amount = _first_amount(fields, BOLETO_AMOUNT_FIELDS)
    due = parse_date(fields.get("data_vencimento"))
    label = boleto.original_filename or str(boleto.id)
    if amount is None:
        errors.append(
            ExportError("amount_missing", f"O boleto {label} está sem valor.")
        )
    if due is None:
        errors.append(
            ExportError("due_date_missing", f"O boleto {label} está sem vencimento.")
        )
    if amount is None or due is None:
        return None
    return Installment(amount, due)


def _installments(
    document: Document,
    kind: str,
    fields: dict[str, Any],
    amount: Decimal | None,
    errors: list[ExportError],
) -> list[Installment]:
    if kind == "boleto":
        due = parse_date(fields.get("data_vencimento"))
        if due is None:
            errors.append(
                ExportError("due_date_missing", "O boleto está sem data de vencimento.")
            )
            return []
        return [Installment(amount, due)] if amount is not None else []

    process = (
        PaymentProcess.objects.filter(
            invoice=document, status=PaymentProcess.Status.CONFIRMED
        )
        .prefetch_related("boletos")
        .first()
    )
    boletos = list(process.boletos.all()) if process else []
    if not boletos:
        errors.append(
            ExportError(
                "due_date_missing",
                "A nota fiscal não traz vencimento. Confirme o processo de pagamento "
                "com o boleto antes de enviar ao ERP.",
            )
        )
        return []
    installments = [
        item
        for item in (_boleto_installment(boleto, errors) for boleto in boletos)
        if item is not None
    ]
    if amount is not None and len(installments) == len(boletos):
        total = sum((i.amount for i in installments), Decimal("0"))
        if abs(total - amount) > _ONE_CENT:
            errors.append(
                ExportError(
                    "amounts_diverge",
                    f"A soma dos boletos ({total:.2f}) é diferente do valor da nota ({amount:.2f}).",
                )
            )
    return sorted(installments, key=lambda i: i.due_date)


def build_draft(document: Document) -> ExpenseDraft:
    """Despesa pronta para enviar. Levanta `DraftInvalid` com todos os problemas."""
    kind = document_kind(document)
    if kind is None:
        raise DraftInvalid(
            [
                ExportError(
                    "document_not_supported",
                    "Só nota fiscal e boleto geram despesa no ERP.",
                )
            ]
        )
    if (
        kind == "boleto"
        and PaymentProcess.objects.filter(
            boletos=document, status=PaymentProcess.Status.CONFIRMED
        ).exists()
    ):
        raise DraftInvalid(
            [
                ExportError(
                    "covered_by_invoice",
                    "Este boleto faz parte de um processo de pagamento. "
                    "A despesa é lançada pela nota fiscal.",
                )
            ]
        )

    errors: list[ExportError] = []
    fields = document_fields(document)
    condominium_id, condominium_name = _check_condominium(document, errors)
    chart_id, account_code, account_name = _check_account(document, errors)
    tax_id, supplier_name = _supplier(fields, kind, errors)

    amount_fields = INVOICE_AMOUNT_FIELDS if kind == "invoice" else BOLETO_AMOUNT_FIELDS
    amount = _first_amount(fields, amount_fields)
    if amount is None:
        errors.append(ExportError("amount_missing", "O documento está sem valor."))

    installments = _installments(document, kind, fields, amount, errors)
    if errors:
        raise DraftInvalid(errors)

    is_invoice = kind == "invoice"
    return ExpenseDraft(
        document_id=str(document.id),
        kind=kind,
        condominium_external_id=condominium_id,
        condominium_name=condominium_name,
        chart_external_id=chart_id,
        account_code=account_code,
        account_name=account_name,
        supplier_tax_id=tax_id,
        supplier_name=supplier_name,
        amount=amount,
        installments=installments,
        issue_date=parse_date(fields.get("data_emissao")) if is_invoice else None,
        competence=_text(fields.get("competencia")) if is_invoice else "",
        document_number=_text(
            fields.get("numero_nota" if is_invoice else "numero_documento")
        ),
        description=_text(fields.get("descricao_servico"))[:200] if is_invoice else "",
    )
