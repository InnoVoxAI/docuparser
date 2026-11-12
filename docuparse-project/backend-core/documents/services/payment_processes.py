"""Processos de pagamento: criação a partir das sugestões do matching."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from django.db import connection, transaction
from django.utils import timezone
from events import PaymentProcessConfirmedEvent, PaymentProcessRejectedEvent
from events.schemas import PaymentProcessDecisionData

from documents.models import Document, DocumentEvent, PaymentProcess

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


class PaymentProcessError(Exception):
    """Decisão que não pode ser aplicada; `code` permite à API explicar ao operador."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


EVENT_SOURCE = "backend-core"


def _record_decision(
    process: PaymentProcess, event_class, user, boleto_ids: list[UUID]
) -> None:
    """Grava quem decidiu e quando, em um DocumentEvent por documento do processo."""
    tenant = connection.tenant
    data = PaymentProcessDecisionData(
        process_id=process.id,
        origin=process.origin.lower(),
        invoice_id=process.invoice_id,
        boleto_ids=boleto_ids,
        decided_by=user.get_username(),
    )
    for document in Document.objects.filter(pk__in=[process.invoice_id, *boleto_ids]):
        event = event_class(
            tenant_id=getattr(tenant, "slug", "") or connection.schema_name,
            document_id=document.id,
            correlation_id=document.correlation_id,
            source=EVENT_SOURCE,
            occurred_at=process.decided_at,
            data=data,
        )
        DocumentEvent.objects.create(
            event_id=event.event_id,
            document=document,
            event_type=event.event_type,
            event_version=event.event_version,
            correlation_id=event.correlation_id,
            source=event.source,
            occurred_at=event.occurred_at,
            payload=event.model_dump(mode="json"),
        )


def _locked_pending(process_id: UUID) -> PaymentProcess:
    process = PaymentProcess.objects.select_for_update().get(pk=process_id)
    if process.status != PaymentProcess.Status.PENDING:
        raise PaymentProcessError(
            "not_pending", "O processo já foi decidido e não aceita nova decisão."
        )
    return process


def confirm_process(process_id: UUID, user) -> PaymentProcess:
    """Operador confirma: o grupo vira processo de pagamento.

    Se a nota já tem processo confirmado (boletos que chegaram depois), os boletos são
    incorporados a ele. Os boletos confirmados saem dos outros pendentes.
    """
    with transaction.atomic():
        process = _locked_pending(process_id)
        Document.objects.select_for_update().get(pk=process.invoice_id)
        boletos = list(process.boletos.all())
        boleto_ids = [boleto.pk for boleto in boletos]
        if not boleto_ids:
            raise PaymentProcessError(
                "no_boletos", "O processo não tem boletos para confirmar."
            )
        taken = (
            PaymentProcess.objects.filter(
                status=PaymentProcess.Status.CONFIRMED, boletos__in=boleto_ids
            )
            .exclude(invoice_id=process.invoice_id)
            .exists()
        )
        if taken:
            raise PaymentProcessError(
                "boleto_taken",
                "Algum boleto já foi confirmado em outro processo de pagamento.",
            )

        now = timezone.now()
        existing = PaymentProcess.objects.filter(
            invoice_id=process.invoice_id, status=PaymentProcess.Status.CONFIRMED
        ).first()
        if existing is not None:
            existing.boletos.add(*boleto_ids)
            process.delete()
            process = existing
        else:
            process.status = PaymentProcess.Status.CONFIRMED
        process.decided_by = user
        process.decided_at = now
        process.save()

        others = PaymentProcess.objects.filter(
            status=PaymentProcess.Status.PENDING, boletos__in=boleto_ids
        ).exclude(pk=process.pk)
        for other in others.distinct():
            other.boletos.remove(*boleto_ids)
            if not other.boletos.exists():
                other.delete()

        _record_decision(
            process,
            PaymentProcessConfirmedEvent,
            user,
            sorted(process.boletos.values_list("pk", flat=True)),
        )
        return process


def reject_process(process_id: UUID, user) -> PaymentProcess:
    """Operador rejeita: os documentos voltam ao pool de documentos sem match."""
    with transaction.atomic():
        process = _locked_pending(process_id)
        process.status = PaymentProcess.Status.REJECTED
        process.decided_by = user
        process.decided_at = timezone.now()
        process.save()
        _record_decision(
            process,
            PaymentProcessRejectedEvent,
            user,
            list(process.boletos.values_list("pk", flat=True)),
        )
        return process
