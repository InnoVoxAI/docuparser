from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings
from django.db import connection
from docuparse_events import event_bus_from_env
from docuparse_observability import log_event
from events import ERPIntegrationRequestedEvent

from documents.models import Document, ERPIntegrationAttempt, IntegrationSettings
from documents.services.approved_exporter import export_approved_document_json

logger = logging.getLogger(__name__)


def _current_tenant_slug() -> str:
    """Document has no tenant FK (multi-tenancy is schema-based, see the
    010-multi-tenancy-schemas migration) — derive the slug from the active
    connection schema the same way documents/services/ocr_processor.py does."""
    schema_name = connection.schema_name or "public"
    return schema_name.removeprefix("tenant_") if schema_name != "public" else "public"


def publish_erp_integration_requested(
    document: Document, connector: str = "mock"
) -> dict:
    tenant_slug = _current_tenant_slug()
    idempotency_key = f"{tenant_slug}:{document.id}:erp:v1"
    attempt, _ = ERPIntegrationAttempt.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "document": document,
            "connector": connector,
            "status": ERPIntegrationAttempt.Status.REQUESTED,
            "request_payload": _canonical_payload(document, tenant_slug),
        },
    )
    if attempt.status != ERPIntegrationAttempt.Status.REQUESTED:
        attempt.status = ERPIntegrationAttempt.Status.REQUESTED
        attempt.save(update_fields=["status", "updated_at"])

    integration_settings = _integration_settings(document)
    export_path = None
    if integration_settings.approved_export_enabled:
        export_path = export_approved_document_json(
            document,
            attempt.request_payload,
            tenant_slug=tenant_slug,
            export_root=integration_settings.approved_export_dir or None,
            export_format=integration_settings.approved_export_format,
        )

    event = ERPIntegrationRequestedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        tenant_id=tenant_slug,
        document_id=document.id,
        correlation_id=document.correlation_id,
        source="backend-core",
        data={
            "connector": connector,
            "payload": attempt.request_payload,
            "idempotency_key": idempotency_key,
            "metadata": {
                "attempt_id": str(attempt.id),
                "approved_export_enabled": integration_settings.approved_export_enabled,
                "approved_export_path": str(export_path) if export_path else "",
                "approved_export_format": integration_settings.approved_export_format,
            },
        },
    ).model_dump(mode="json")

    event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR).publish(
        "erp.integration.requested", event
    )
    document.transition_to(Document.Status.ERP_INTEGRATION_REQUESTED)
    log_event(
        logger,
        "erp.integration.requested published",
        tenant_id=tenant_slug,
        document_id=str(document.id),
        correlation_id=str(document.correlation_id),
        event_type="erp.integration.requested",
        approved_export_path=str(export_path) if export_path else "",
    )
    return event


def _canonical_payload(document: Document, tenant_slug: str) -> dict:
    extraction = getattr(document, "extraction_result", None)
    return {
        "document_id": str(document.id),
        "tenant_id": tenant_slug,
        "schema_id": extraction.schema_id if extraction else None,
        "schema_version": extraction.schema_version if extraction else None,
        "fields": extraction.fields if extraction else {},
        "source": {
            "channel": document.channel,
            "file_uri": document.file_uri,
            "raw_text_uri": document.raw_text_uri,
        },
    }


def _integration_settings(document: Document) -> IntegrationSettings:
    from documents.models import SETTINGS_SINGLETON_ID

    settings_obj, _ = IntegrationSettings.objects.get_or_create(
        id=SETTINGS_SINGLETON_ID,
        defaults={
            "approved_export_enabled": True,
            "approved_export_dir": settings.DOCUPARSE_APPROVED_EXPORT_DIR,
            "approved_export_format": IntegrationSettings.ExportFormat.JSON,
            "superlogica_mode": IntegrationSettings.SuperlogicaMode.DISABLED,
        },
    )
    return settings_obj
