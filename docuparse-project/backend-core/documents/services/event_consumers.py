from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_datetime

from events import (
    DocumentReceivedEvent,
    ERPFailedEvent,
    ERPSentEvent,
    ExtractionCompletedEvent,
    OCRCompletedEvent,
    OCRFailedEvent,
)
from docuparse_observability import log_event

from documents.models import (
    Document,
    DocumentEvent,
    ERPIntegrationAttempt,
    ExtractionResult,
    Tenant,
)

logger = logging.getLogger(__name__)


def consume_document_received(payload: dict[str, Any]) -> Document:
    event = DocumentReceivedEvent.model_validate(payload)
    with transaction.atomic():
        tenant = _tenant_for(event.tenant_id)
        existing_event, created = _record_event_once(event, tenant)
        if not created and existing_event.document_id:
            return existing_event.document

        document, _ = Document.objects.get_or_create(
            id=event.document_id,
            defaults={
                "tenant": tenant,
                "status": Document.Status.RECEIVED,
                "channel": event.data.channel,
                "file_uri": event.data.file.uri,
                "original_filename": event.data.file.filename,
                "content_type": event.data.file.content_type,
                "size_bytes": event.data.file.size_bytes,
                "correlation_id": event.correlation_id,
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


def consume_extraction_completed(payload: dict[str, Any]) -> Document:
    event = ExtractionCompletedEvent.model_validate(payload)
    with transaction.atomic():
        tenant = _tenant_for(event.tenant_id)
        existing_event, created = _record_event_once(event, tenant)
        document = Document.objects.select_for_update().get(id=event.document_id, tenant=tenant)
        if not created and existing_event.document_id:
            return document

        ExtractionResult.objects.update_or_create(
            document=document,
            defaults={
                "schema_id": event.data.schema_id,
                "schema_version": event.data.schema_version,
                "fields": event.data.fields,
                "confidence": event.data.confidence,
                "requires_human_validation": event.data.requires_human_validation,
            },
        )
        document.status = (
            Document.Status.VALIDATION_PENDING
            if event.data.requires_human_validation
            else Document.Status.EXTRACTION_COMPLETED
        )
        document.save(update_fields=["status", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        log_event(
            logger,
            "extraction.completed consumed",
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            correlation_id=str(event.correlation_id),
            event_type=event.event_type,
            status=document.status,
        )
        return document


def consume_ocr_completed(payload: dict[str, Any]) -> Document:
    event = OCRCompletedEvent.model_validate(payload)
    with transaction.atomic():
        tenant = _tenant_for(event.tenant_id)
        existing_event, created = _record_event_once(event, tenant)
        document = Document.objects.select_for_update().get(id=event.document_id, tenant=tenant)
        if not created and existing_event.document_id:
            return document

        document.raw_text_uri = event.data.raw_text_uri
        document.document_type = event.data.document_type if event.data.document_type != "unknown" else document.document_type
        document.status = Document.Status.OCR_COMPLETED
        document.metadata = {
            **(document.metadata or {}),
            "ocr": {
                "engine_used": event.data.engine_used,
                "confidence": event.data.confidence,
                "processing_time_seconds": event.data.processing_time_seconds,
                "artifacts": event.data.artifacts,
                "metadata": event.data.metadata,
            },
        }
        document.save(update_fields=["raw_text_uri", "document_type", "status", "metadata", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        log_event(
            logger,
            "ocr.completed consumed",
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            correlation_id=str(event.correlation_id),
            event_type=event.event_type,
            raw_text_uri=event.data.raw_text_uri,
        )
        return document


def consume_ocr_failed(payload: dict[str, Any]) -> Document:
    event = OCRFailedEvent.model_validate(payload)
    with transaction.atomic():
        tenant = _tenant_for(event.tenant_id)
        existing_event, created = _record_event_once(event, tenant)
        document = Document.objects.select_for_update().get(id=event.document_id, tenant=tenant)
        if not created and existing_event.document_id:
            return document

        document.status = Document.Status.OCR_FAILED
        document.metadata = {
            **(document.metadata or {}),
            "ocr_error": {
                "reason": event.data.reason,
                "retryable": event.data.retryable,
                "engine_used": event.data.engine_used,
                "metadata": event.data.metadata,
            },
        }
        document.save(update_fields=["status", "metadata", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        log_event(
            logger,
            "ocr.failed consumed",
            level=logging.ERROR,
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            correlation_id=str(event.correlation_id),
            event_type=event.event_type,
            reason=event.data.reason,
        )
        return document


def consume_erp_sent(payload: dict[str, Any]) -> Document:
    event = ERPSentEvent.model_validate(payload)
    with transaction.atomic():
        tenant = _tenant_for(event.tenant_id)
        existing_event, created = _record_event_once(event, tenant)
        document = Document.objects.select_for_update().get(id=event.document_id, tenant=tenant)
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
            },
        )
        document.status = Document.Status.ERP_SENT
        document.save(update_fields=["status", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        return document


def consume_erp_failed(payload: dict[str, Any]) -> Document:
    event = ERPFailedEvent.model_validate(payload)
    with transaction.atomic():
        tenant = _tenant_for(event.tenant_id)
        existing_event, created = _record_event_once(event, tenant)
        document = Document.objects.select_for_update().get(id=event.document_id, tenant=tenant)
        if not created and existing_event.document_id:
            return document

        ERPIntegrationAttempt.objects.update_or_create(
            idempotency_key=event.data.idempotency_key,
            defaults={
                "document": document,
                "connector": event.data.connector,
                "status": ERPIntegrationAttempt.Status.FAILED,
                "response_payload": {
                    **event.data.response_metadata,
                    "reason": event.data.reason,
                    "retryable": event.data.retryable,
                },
            },
        )
        document.status = Document.Status.ERP_FAILED
        document.save(update_fields=["status", "updated_at"])
        existing_event.document = document
        existing_event.save(update_fields=["document", "updated_at"])
        return document


def _tenant_for(tenant_id: str) -> Tenant:
    tenant, _ = Tenant.objects.get_or_create(
        slug=tenant_id,
        defaults={
            "name": tenant_id,
        },
    )
    return tenant


def _record_event_once(event, tenant: Tenant) -> tuple[DocumentEvent, bool]:
    existing = DocumentEvent.objects.filter(event_id=event.event_id).first()
    if existing:
        return existing, False

    return (
        DocumentEvent.objects.create(
            event_id=event.event_id,
            tenant=tenant,
            document_id=event.document_id if Document.objects.filter(id=event.document_id).exists() else None,
            event_type=event.event_type,
            event_version=event.event_version,
            correlation_id=event.correlation_id,
            source=event.source,
            occurred_at=event.occurred_at,
            payload=event.model_dump(mode="json"),
        ),
        True,
    )
