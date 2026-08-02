from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.test import TestCase
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from tenants.models import Tenant

from documents.services.event_consumers import consume_document_received


class ApplicationErrorTracingTests(TestCase):
    """T054 — um erro de aplicação numa etapa intermediária do fluxo de
    documento (consumo assíncrono do evento document.received) fica
    correlacionado ao trace, sem vazamento de dado sensível (US4)."""

    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-demo", name="Tenant Demo")
        connection.set_tenant(self.tenant)
        self.exporter = InMemorySpanExporter()
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(self.exporter)
        )

    def _document_received_payload(self) -> dict:
        document_id = uuid4()
        return {
            "event_id": str(uuid4()),
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
                    "filename": "fixture-with-personal-name.pdf",
                    "size_bytes": 1024,
                    "sha256": "a" * 64,
                },
                "metadata": {"source": "test"},
            },
        }

    def test_unhandled_exception_in_document_processing_marks_span_as_error(
        self,
    ) -> None:
        payload = self._document_received_payload()

        with patch(
            "documents.services.event_consumers.Document.objects.get_or_create",
            side_effect=RuntimeError("boom - simulated application bug"),
        ):
            with self.assertRaises(RuntimeError):
                consume_document_received(payload)

        processing_spans = [
            span
            for span in self.exporter.get_finished_spans()
            if span.name == "document.received process"
        ]
        assert len(processing_spans) == 1
        span = processing_spans[0]

        assert span.status.status_code == trace.StatusCode.ERROR

        exception_events = [event for event in span.events if event.name == "exception"]
        assert len(exception_events) == 1
        assert exception_events[0].attributes.get("exception.type") == "RuntimeError"

        forbidden_substrings = (
            payload["data"]["file"]["filename"],
            payload["data"]["sender"],
        )
        for attributes in (span.attributes, exception_events[0].attributes):
            for value in attributes.values():
                rendered = str(value)
                for forbidden in forbidden_substrings:
                    assert forbidden not in rendered
