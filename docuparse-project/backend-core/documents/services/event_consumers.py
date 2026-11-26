from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from django.db import transaction
from docuparse_events import extract_trace_link
from docuparse_observability import log_event
from events import (
    DocumentReceivedEvent,
    ERPFailedEvent,
    ERPSentEvent,
)
from opentelemetry import trace

from documents.models import (
    Document,
    DocumentEvent,
    ERPIntegrationAttempt,
)
from documents.services import erp_retry
from documents.services.erp_retry import FINGERPRINT_KEY, STARTED_KEY

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)

F = TypeVar("F", bound=Callable[[dict], Any])


def _traced_consumer(span_name: str) -> Callable[[F], F]:
    """Inicia o span de processamento com um Link para o trace de origem do
    evento (research.md R4), quando `trace_context` estiver presente."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(payload: dict[str, Any]) -> Any:
            link = extract_trace_link(payload)
            with _tracer.start_as_current_span(span_name, links=[link] if link else []):
                return func(payload)

        return wrapper  # type: ignore[return-value]

    return decorator


class DuplicateDocumentError(Exception):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"O Documento '{filename}' já existe!")


@_traced_consumer("document.received process")
def consume_document_received(payload: dict[str, Any]) -> Document:
    event = DocumentReceivedEvent.model_validate(payload)
    with transaction.atomic():
        existing_event, created = _record_event_once(event)
        if not created and existing_event.document_id:
            return existing_event.document

        sha256 = event.data.file.sha256 or ""
        filename = event.data.file.filename
        if filename and Document.objects.filter(original_filename=filename).exists():
            raise DuplicateDocumentError(filename)

        document, _ = Document.objects.get_or_create(
            id=event.document_id,
            defaults={
                "status": Document.Status.RECEIVED,
                "channel": event.data.channel,
                "file_uri": event.data.file.uri,
                "original_filename": event.data.file.filename,
                "content_type": event.data.file.content_type,
                "size_bytes": event.data.file.size_bytes,
                "sha256": sha256,
                "correlation_id": event.correlation_id,
                "source_thread_id": event.data.source_thread_id,
                "received_at": event.data.received_at,
                "metadata": event.data.metadata,
            },
        )
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        log_event(
            logger,
            "document.received consumed",
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            correlation_id=str(event.correlation_id),
            event_type=event.event_type,
        )
        return document


@_traced_consumer("erp.integration.requested process")
def consume_erp_integration_requested(payload: dict[str, Any]) -> Any:
    """Executa o conector do tenant e publica `erp.sent` ou `erp.failed`.

    O conector roda fora de qualquer transação: não há chamada de rede com lock de
    banco aberto. A idempotência do evento fica no registro único em `DocumentEvent`.
    """
    from django.conf import settings
    from docuparse_events import event_bus_from_env
    from erp_export.connector import execute
    from erp_export.outcome import publish_outcome
    from events import ERPIntegrationRequestedEvent

    from documents.services.erp_mock import handle_erp_integration_requested_event

    event = ERPIntegrationRequestedEvent.model_validate(payload)
    with transaction.atomic():
        existing_event, created = _record_event_once(event)
    if not created:
        return None

    try:
        result = execute(event.document_id, event.data.idempotency_key)
    except Exception as exc:
        # Erro inesperado: o documento não pode ficar preso em "ERP solicitado".
        # Retentável e com resultado incerto, para a próxima tentativa reconciliar.
        from erp_export.connector import ConnectorResult
        from erp_export.errors import ExportError

        logger.error(
            "erp_connector_unexpected_error | document_id=%s | error=%s",
            event.document_id,
            type(exc).__name__,
        )
        result = ConnectorResult(
            "failed",
            error=ExportError(
                "internal_error",
                "Erro interno ao enviar ao ERP. Tente de novo.",
                retryable=True,
                outcome_unknown=True,
            ),
        )
    log_event(
        logger,
        "erp.integration.requested processed",
        tenant_id=event.tenant_id,
        document_id=str(event.document_id),
        correlation_id=str(event.correlation_id),
        event_type=event.event_type,
        result=result.kind,
        error_code=result.error.code if result.error else "",
    )

    if result.kind == "mock":
        bus = event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR)
        sent_event = handle_erp_integration_requested_event(payload, bus)
        consume_erp_sent(sent_event)
    elif result.kind == "dry_run":
        _record_dry_run(event, result.detail.get("preview", {}))
    else:
        publish_outcome(event, result)
    return result


def _record_dry_run(event: Any, preview: dict[str, Any]) -> None:
    """Simulação concluída: nada foi enviado, então o documento volta a "aprovado"."""
    from datetime import datetime, timezone

    from events import ERPDryRunEvent

    document = Document.objects.get(id=event.document_id)
    dry_run = ERPDryRunEvent(
        tenant_id=event.tenant_id,
        document_id=document.id,
        correlation_id=document.correlation_id,
        source="erp-superlogica",
        occurred_at=datetime.now(timezone.utc),
        data={
            "idempotency_key": event.data.idempotency_key,
            "connector": event.data.connector,
            "preview": preview,
        },
    )
    DocumentEvent.objects.create(
        event_id=dry_run.event_id,
        document=document,
        event_type=dry_run.event_type,
        event_version=dry_run.event_version,
        correlation_id=dry_run.correlation_id,
        source=dry_run.source,
        occurred_at=dry_run.occurred_at,
        payload=dry_run.model_dump(mode="json"),
    )
    document.transition_to(Document.Status.APPROVED)


@_traced_consumer("erp.sent process")
def consume_erp_sent(payload: dict[str, Any]) -> Document:
    event = ERPSentEvent.model_validate(payload)
    with transaction.atomic():
        existing_event, created = _record_event_once(event)
        document = Document.objects.select_for_update().get(id=event.document_id)
        if not created and existing_event.document_id:
            return document

        ERPIntegrationAttempt.objects.update_or_create(
            idempotency_key=event.data.idempotency_key,
            defaults={
                "document": document,
                "connector": event.data.connector,
                "status": ERPIntegrationAttempt.Status.SENT,
                "external_id": event.data.external_id or "",
                "response_payload": event.data.response_metadata,
                "next_retry_at": None,
            },
        )
        document.status = Document.Status.ERP_SENT
        document.save(update_fields=["status", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        return document


@_traced_consumer("erp.failed process")
def consume_erp_failed(payload: dict[str, Any]) -> Document:
    event = ERPFailedEvent.model_validate(payload)
    with transaction.atomic():
        existing_event, created = _record_event_once(event)
        document = Document.objects.select_for_update().get(id=event.document_id)
        if not created and existing_event.document_id:
            return document

        previous = ERPIntegrationAttempt.objects.filter(
            idempotency_key=event.data.idempotency_key
        ).first()
        attempt, _ = ERPIntegrationAttempt.objects.update_or_create(
            idempotency_key=event.data.idempotency_key,
            defaults={
                "document": document,
                "connector": event.data.connector,
                "status": ERPIntegrationAttempt.Status.FAILED,
                "response_payload": {
                    **event.data.response_metadata,
                    "reason": event.data.reason,
                    "retryable": event.data.retryable,
                    # O marcador de "envio iniciado" sobrevive à falha: é ele que
                    # faz a próxima tentativa reconciliar em vez de reenviar às cegas.
                    **{
                        key: previous.response_payload[key]
                        for key in (STARTED_KEY, FINGERPRINT_KEY)
                        if previous and key in (previous.response_payload or {})
                    },
                },
            },
        )
        if event.data.retryable:
            attempt.retry_count += 1
            attempt.next_retry_at = erp_retry.next_retry_at(attempt.retry_count)
        else:
            attempt.next_retry_at = None
        attempt.save(update_fields=["retry_count", "next_retry_at", "updated_at"])
        document.status = Document.Status.ERP_FAILED
        document.save(update_fields=["status", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        return document


def _record_event_once(event: object) -> tuple[DocumentEvent, bool]:
    existing = DocumentEvent.objects.filter(event_id=event.event_id).first()
    if existing:
        return existing, False

    return (
        DocumentEvent.objects.create(
            event_id=event.event_id,
            document_id=event.document_id
            if Document.objects.filter(id=event.document_id).exists()
            else None,
            event_type=event.event_type,
            event_version=event.event_version,
            correlation_id=event.correlation_id,
            source=event.source,
            occurred_at=event.occurred_at,
            payload=event.model_dump(mode="json"),
        ),
        True,
    )
