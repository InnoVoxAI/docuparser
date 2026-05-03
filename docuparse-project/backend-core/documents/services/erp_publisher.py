from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings

from docuparse_events import event_bus_from_env
from docuparse_observability import log_event
from events import ERPIntegrationRequestedEvent

from documents.models import Document, ERPIntegrationAttempt
from documents.services.approved_exporter import export_approved_document_json

logger = logging.getLogger(__name__)


def publish_erp_integration_requested(document: Document, connector: str = "mock") -> dict:
    idempotency_key = f"{document.tenant.slug}:{document.id}:erp:v1"
    attempt, _ = ERPIntegrationAttempt.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "document": document,
            "connector": connector,
            "status": ERPIntegrationAttempt.Status.REQUESTED,
            "request_payload": _canonical_payload(document),
        },
    )
    if attempt.status != ERPIntegrationAttempt.Status.REQUESTED:
        attempt.status = ERPIntegrationAttempt.Status.REQUESTED
        attempt.save(update_fields=["status", "updated_at"])

    export_path = export_approved_document_json(document, attempt.request_payload)

    event = ERPIntegrationRequestedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        tenant_id=document.tenant.slug,
        document_id=document.id,
        correlation_id=document.correlation_id,
        source="backend-core",
        data={
            "connector": connector,
            "payload": attempt.request_payload,
            "idempotency_key": idempotency_key,
            "metadata": {
                "attempt_id": str(attempt.id),
                "approved_export_path": str(export_path),
            },
        },
    ).model_dump(mode="json")

    event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR).publish("erp.integration.requested", event)
    document.transition_to(Document.Status.ERP_INTEGRATION_REQUESTED)
    log_event(
        logger,
        "erp.integration.requested published",
        tenant_id=document.tenant.slug,
        document_id=str(document.id),
        correlation_id=str(document.correlation_id),
        event_type="erp.integration.requested",
        approved_export_path=str(export_path),
    )
    return event


def _canonical_payload(document: Document) -> dict:
    extraction = getattr(document, "extraction_result", None)
    return {
        "document_id": str(document.id),
        "tenant_id": document.tenant.slug,
        "schema_id": extraction.schema_id if extraction else None,
        "schema_version": extraction.schema_version if extraction else None,
        "fields": extraction.fields if extraction else {},
        "source": {
            "channel": document.channel,
            "file_uri": document.file_uri,
            "raw_text_uri": document.raw_text_uri,
        },
    }
