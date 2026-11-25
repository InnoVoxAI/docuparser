"""Casamento entre nota fiscal e boleto pelo CNPJ do fornecedor e pelo valor.

Regras (CNPJ do fornecedor na nota igual ao do beneficiário no boleto):
- mesmo valor: casa;
- boleto de valor menor que a nota: casa (a nota pode ter vários boletos, em parcelas);
- boleto de valor maior que a nota: não casa;
- CNPJ diferente: não casa.

Cada boleto é avaliado sozinho contra a nota; a soma das parcelas não é limitada.
O resultado é só uma sugestão (`PaymentProcess` pendente): a confirmação humana vem depois.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from condominiums.tax_ids import is_valid_cnpj, normalize_tax_id
from django.conf import settings
from django.db.models import Q

from documents.models import Document, ExtractionResult, PaymentProcess
from documents.services.field_versioning import get_active_version
from documents.services.payment_processes import suggest_boletos

logger = logging.getLogger(__name__)

Kind = Literal["invoice", "boleto"]

# Campos que identificam o papel do documento: CNPJ de quem cobra e valor a pagar.
INVOICE_TAX_ID_FIELD = "cnpj_fornecedor"
INVOICE_AMOUNT_FIELDS = ("valor_nota",)
BOLETO_TAX_ID_FIELD = "cnpj_cpf_beneficiario"
BOLETO_AMOUNT_FIELDS = ("valor_boleto", "valor_documento")

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class PaymentCandidate:
    document_id: Any
    kind: Kind
    tax_id: str
    amount: Decimal


def parse_amount(value: Any) -> Decimal | None:
    """Valor monetário extraído (número ou texto "1.470,15" / "1470.15") em Decimal."""
    if isinstance(value, bool) or value in (None, ""):
        return None
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return amount.quantize(_CENT) if amount.is_finite() else None


def build_candidate(
    document_id: Any, fields: dict[str, Any]
) -> PaymentCandidate | None:
    """Papel (nota ou boleto), CNPJ e valor do documento; None se não der para casar."""
    for kind, tax_id_field, amount_fields in (
        ("invoice", INVOICE_TAX_ID_FIELD, INVOICE_AMOUNT_FIELDS),
        ("boleto", BOLETO_TAX_ID_FIELD, BOLETO_AMOUNT_FIELDS),
    ):
        if tax_id_field not in fields:
            continue
        tax_id = normalize_tax_id(str(fields[tax_id_field]))
        amount = next(
            (
                a
                for f in amount_fields
                if (a := parse_amount(fields.get(f))) is not None
            ),
            None,
        )
        # Boleto de CPF não é de fornecedor pessoa jurídica: só CNPJ válido casa.
        if amount is None or amount <= 0 or not is_valid_cnpj(tax_id):
            return None
        return PaymentCandidate(document_id, kind, tax_id, amount)  # type: ignore[arg-type]
    return None


def is_match(invoice: PaymentCandidate, boleto: PaymentCandidate) -> bool:
    """Mesmo CNPJ e boleto de valor menor ou igual ao da nota."""
    return invoice.tax_id == boleto.tax_id and boleto.amount <= invoice.amount


def _plain_fields(document: Document) -> dict[str, Any]:
    """Campos vigentes (versão ativa, se houver) como valores simples."""
    version = get_active_version(document)
    extraction = ExtractionResult.objects.filter(document=document).first()
    raw_fields = (
        version.fields if version else (extraction.fields if extraction else {})
    )
    return {
        name: raw.get("value") if isinstance(raw, dict) else raw
        for name, raw in raw_fields.items()
    }


def document_fields(document: Document) -> dict[str, Any]:
    """Campos vigentes (versão ativa, se houver) como valores simples."""
    return _plain_fields(document)


def candidate_for(document: Document) -> PaymentCandidate | None:
    return build_candidate(document.id, _plain_fields(document))


INVOICE_KEYS = (INVOICE_TAX_ID_FIELD, *INVOICE_AMOUNT_FIELDS)
BOLETO_KEYS = (BOLETO_TAX_ID_FIELD, *BOLETO_AMOUNT_FIELDS)


def document_kind(document: Document) -> Kind | None:
    """Nota fiscal ou boleto, pelos campos que o schema extrai (mesmo sem valor lido).

    Serve ao pareamento manual: um boleto cujo CNPJ o OCR leu pela metade ainda é um
    boleto, só não casa sozinho.
    """
    fields = _plain_fields(document)
    if any(key in fields for key in INVOICE_KEYS):
        return "invoice"
    if any(key in fields for key in BOLETO_KEYS):
        return "boleto"
    return None


def run_payment_matching(document: Document) -> list[PaymentProcess]:
    """Procura, na janela de tempo, os documentos do papel oposto que casam com este.

    Devolve os processos pendentes que ganharam boletos; pares já sugeridos, rejeitados
    ou confirmados não voltam.
    """
    candidate = candidate_for(document)
    if candidate is None:
        return []

    window = timedelta(hours=settings.PAYMENT_MATCH_WINDOW_HOURS)
    opposite_field = (
        BOLETO_TAX_ID_FIELD if candidate.kind == "invoice" else INVOICE_TAX_ID_FIELD
    )
    others = (
        Document.objects.filter(
            received_at__range=(
                document.received_at - window,
                document.received_at + window,
            )
        )
        .exclude(pk=document.pk)
        .exclude(status=Document.Status.REJECTED)
        .filter(
            Q(extraction_result__fields__has_key=opposite_field)
            | Q(
                field_versions__is_active=True,
                field_versions__fields__has_key=opposite_field,
            )
        )
        .distinct()
    )

    boletos_by_invoice: dict[Any, set[Any]] = {}
    for other in others:
        other_candidate = candidate_for(other)
        if other_candidate is None or other_candidate.kind == candidate.kind:
            continue
        invoice, boleto = (
            (candidate, other_candidate)
            if candidate.kind == "invoice"
            else (other_candidate, candidate)
        )
        if is_match(invoice, boleto):
            boletos_by_invoice.setdefault(invoice.document_id, set()).add(
                boleto.document_id
            )

    touched = (
        suggest_boletos(invoice_id, boleto_ids)
        for invoice_id, boleto_ids in boletos_by_invoice.items()
    )
    return [process for process in touched if process is not None]


def run_payment_matching_safely(document: Document) -> list[PaymentProcess]:
    """Versão para o pipeline: o casamento nunca derruba o processamento."""
    try:
        return run_payment_matching(document)
    except Exception:
        logger.error(
            "payment_matching_failed",
            exc_info=True,
            extra={"document_id": str(document.id)},
        )
        return []
