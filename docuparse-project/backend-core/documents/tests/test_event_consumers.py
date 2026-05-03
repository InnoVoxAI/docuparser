from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from django.test import TestCase

from documents.models import Document, DocumentEvent, ERPIntegrationAttempt, ExtractionResult, Tenant
from documents.services.event_consumers import (
    consume_document_received,
    consume_erp_failed,
    consume_erp_sent,
    consume_extraction_completed,
)


class CoreEventConsumerTests(TestCase):
    def _document_received_payload(self, document_id=None, event_id=None) -> dict:
        document_id = document_id or uuid4()
        return {
            "event_id": str(event_id or uuid4()),
            "event_type": "document.received",
            "event_version": "v1",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": "tenant-demo",
            "document_id": str(document_id),
            "correlation_id": str(uuid4()),
            "source": "backend-com",
            "data": {
                "channel": "manual",
                "received_at": datetime.now(timezone.utc).isoformat(),
                "sender": "operator@example.test",
                "file": {
                    "uri": f"local://documents/tenant-demo/{document_id}/original",
                    "content_type": "application/pdf",
                    "filename": "fixture.pdf",
                    "size_bytes": 1024,
                    "sha256": "a" * 64,
                },
                "metadata": {"source": "test"},
            },
        }

    def test_consume_document_received_creates_tenant_document_and_event_idempotently(self) -> None:
        payload = self._document_received_payload()

        first = consume_document_received(payload)
        second = consume_document_received(payload)

        assert first.id == second.id
        assert Tenant.objects.count() == 1
        assert Document.objects.count() == 1
        assert DocumentEvent.objects.count() == 1
        assert first.status == Document.Status.RECEIVED
        assert first.file_uri == payload["data"]["file"]["uri"]

    def test_consume_extraction_completed_updates_document_and_is_idempotent(self) -> None:
        document = consume_document_received(self._document_received_payload())
        payload = {
            "event_id": str(uuid4()),
            "event_type": "extraction.completed",
            "event_version": "v1",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": "tenant-demo",
            "document_id": str(document.id),
            "correlation_id": str(document.correlation_id),
            "source": "langextract-service",
            "data": {
                "schema_id": "boleto",
                "schema_version": "v1",
                "fields": {"valor": "R$ 123,45"},
                "confidence": 0.6,
                "requires_human_validation": True,
                "metadata": {},
            },
        }

        consume_extraction_completed(payload)
        consume_extraction_completed(payload)

        document.refresh_from_db()
        assert document.status == Document.Status.VALIDATION_PENDING
        assert ExtractionResult.objects.count() == 1
        assert DocumentEvent.objects.filter(event_type="extraction.completed").count() == 1

    def test_consume_erp_sent_and_failed_update_attempts_and_state(self) -> None:
        document = consume_document_received(self._document_received_payload())
        sent_payload = {
            "event_id": str(uuid4()),
            "event_type": "erp.sent",
            "event_version": "v1",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": "tenant-demo",
            "document_id": str(document.id),
            "correlation_id": str(document.correlation_id),
            "source": "backend-conect",
            "data": {
                "connector": "mock",
                "external_id": "mock-123",
                "idempotency_key": f"tenant-demo:{document.id}:v1",
                "response_metadata": {"status": 200},
            },
        }
        failed_payload = {
            **sent_payload,
            "event_id": str(uuid4()),
            "event_type": "erp.failed",
            "data": {
                "connector": "mock",
                "reason": "timeout",
                "retryable": True,
                "idempotency_key": f"tenant-demo:{document.id}:v2",
                "response_metadata": {},
            },
        }

        consume_erp_sent(sent_payload)
        document.refresh_from_db()
        assert document.status == Document.Status.ERP_SENT

        consume_erp_failed(failed_payload)
        document.refresh_from_db()
        assert document.status == Document.Status.ERP_FAILED
        assert ERPIntegrationAttempt.objects.count() == 2
