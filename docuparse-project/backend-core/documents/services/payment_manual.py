"""Pareamento manual de nota fiscal e boletos, para quando o automático não casou."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet

from documents.models import Document, PaymentProcess
from documents.services.payment_matching import (
    BOLETO_KEYS,
    INVOICE_KEYS,
    Kind,
    document_kind,
)
from documents.services.payment_processes import PaymentProcessError

_TAKEN = (PaymentProcess.Status.PENDING, PaymentProcess.Status.CONFIRMED)


def unmatched_documents(kind: Kind) -> QuerySet[Document]:
    """Notas (ou boletos) fora de qualquer processo pendente ou confirmado.

    Documentos de um agrupamento rejeitado voltam para cá.
    """
    keys = INVOICE_KEYS if kind == "invoice" else BOLETO_KEYS
    relation = (
        "payment_processes_as_invoice"
        if kind == "invoice"
        else "payment_processes_as_boleto"
    )
    return (
        Document.objects.filter(
            Q(extraction_result__fields__has_any_keys=keys)
            | Q(
                field_versions__is_active=True,
                field_versions__fields__has_any_keys=keys,
            )
        )
        .exclude(status=Document.Status.REJECTED)
        .exclude(**{f"{relation}__status__in": _TAKEN})
        .select_related("extraction_result")
        .distinct()
        .order_by("-received_at")
    )


def create_manual_process(
    invoice_id: UUID, boleto_ids: Iterable[UUID]
) -> PaymentProcess:
    """Operador monta o par à mão. Nasce pendente e segue o mesmo fluxo de confirmação.

    Não exige CNPJ nem valor iguais: o automático já tentou, e o operador decide.
    """
    wanted = set(boleto_ids)
    if not wanted:
        raise PaymentProcessError("no_boletos", "Escolha ao menos um boleto.")
    with transaction.atomic():
        invoice = Document.objects.select_for_update().filter(pk=invoice_id).first()
        boletos = list(Document.objects.filter(pk__in=wanted))
        if invoice is None or len(boletos) != len(wanted):
            raise PaymentProcessError("not_found", "Documento não encontrado.")
        if document_kind(invoice) != "invoice" or any(
            document_kind(b) != "boleto" for b in boletos
        ):
            raise PaymentProcessError(
                "wrong_kind", "Escolha uma nota fiscal e boletos."
            )
        if PaymentProcess.objects.filter(
            invoice=invoice, status=PaymentProcess.Status.PENDING
        ).exists():
            raise PaymentProcessError(
                "invoice_busy",
                "A nota já tem um agrupamento aguardando decisão. Decida-o primeiro.",
            )
        if PaymentProcess.objects.filter(
            boletos__in=boletos, status__in=_TAKEN
        ).exists():
            raise PaymentProcessError(
                "boleto_unavailable",
                "Algum boleto já está em um agrupamento pendente ou confirmado.",
            )
        process = PaymentProcess.objects.create(
            invoice=invoice, origin=PaymentProcess.Origin.MANUAL
        )
        process.boletos.add(*boletos)
        return process


def undo_manual_process(process_id: UUID) -> None:
    """Desfaz a seleção manual antes da confirmação: os documentos voltam ao pool."""
    with transaction.atomic():
        process = PaymentProcess.objects.select_for_update().get(pk=process_id)
        if process.status != PaymentProcess.Status.PENDING:
            raise PaymentProcessError(
                "not_pending", "O processo já foi decidido e não pode ser desfeito."
            )
        if process.origin != PaymentProcess.Origin.MANUAL:
            raise PaymentProcessError(
                "not_manual",
                "Só a seleção manual pode ser desfeita; rejeite a sugestão automática.",
            )
        process.delete()
