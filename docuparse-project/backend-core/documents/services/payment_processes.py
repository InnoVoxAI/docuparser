"""Processos de pagamento: criação a partir das sugestões do matching."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from django.db import transaction

from documents.models import Document, PaymentProcess

_OPEN_OR_DECIDED = (
    PaymentProcess.Status.PENDING,
    PaymentProcess.Status.CONFIRMED,
    PaymentProcess.Status.REJECTED,
)


def suggest_boletos(
    invoice_id: UUID, boleto_ids: Iterable[UUID]
) -> PaymentProcess | None:
    """Junta boletos ao processo pendente da nota (criando-o se faltar).

    Ignora o que já foi decidido: boleto que já está num processo desta nota (pendente,
    confirmado ou rejeitado) e boleto confirmado em processo de outra nota. Devolve o
    processo que ganhou boletos, ou None se não havia nada novo.
    """
    with transaction.atomic():
        # Trava a nota para duas chegadas simultâneas não criarem dois pendentes.
        Document.objects.select_for_update().get(pk=invoice_id)
        wanted = set(boleto_ids)
        known = set(
            Document.objects.filter(
                payment_processes_as_boleto__invoice_id=invoice_id,
                payment_processes_as_boleto__status__in=_OPEN_OR_DECIDED,
            ).values_list("pk", flat=True)
        )
        taken_elsewhere = set(
            Document.objects.filter(
                pk__in=wanted,
                payment_processes_as_boleto__status=PaymentProcess.Status.CONFIRMED,
            )
            .exclude(payment_processes_as_boleto__invoice_id=invoice_id)
            .values_list("pk", flat=True)
        )
        new = wanted - known - taken_elsewhere
        if not new:
            return None
        process = PaymentProcess.objects.filter(
            invoice_id=invoice_id, status=PaymentProcess.Status.PENDING
        ).first() or PaymentProcess.objects.create(
            invoice_id=invoice_id, origin=PaymentProcess.Origin.AUTOMATIC
        )
        process.boletos.add(*new)
        return process
