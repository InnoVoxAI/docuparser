from __future__ import annotations

from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from uuid import uuid4

from django.test import TestCase

from docuparse_events import LocalJsonlEventBus

from documents.models import Document, DocumentEvent
from documents.services.event_stream_worker import CoreEventStreamWorker


class CoreEventStreamWorkerTests(TestCase):
    def test_worker_consumes_document_and_ocr_events_from_event_bus(self) -> None:
        document_id = uuid4()
        correlation_id = uuid4()
        event_dir = TemporaryDirectory()
        self.addCleanup(event_dir.cleanup)
        event_bus = LocalJsonlEventBus(event_dir.name)
        event_bus.publish(
            "document.received",
            {
                "event_id": str(uuid4()),
                "event_type": "document.received",
                "event_version": "v1",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": "tenant-demo",
                "document_id": str(document_id),
                "correlation_id": str(correlation_id),
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
                    "metadata": {},
                },
            },
        )
        event_bus.publish(
            "ocr.completed",
            {
                "event_id": str(uuid4()),
                "event_type": "ocr.completed",
                "event_version": "v1",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "tenant_id": "tenant-demo",
                "document_id": str(document_id),
                "correlation_id": str(correlation_id),
                "source": "backend-ocr",
                "data": {
                    "raw_text_uri": f"local://documents/tenant-demo/{document_id}/ocr/raw_text.json",
                    "raw_text_preview": "texto",
                    "document_type": "digital_pdf",
                    "engine_used": "docling",
                    "confidence": None,
                    "processing_time_seconds": 0.12,
                    "artifacts": {},
                    "metadata": {},
                },
            },
        )

        worker = CoreEventStreamWorker(event_bus=event_bus, start_at_latest=False)

        assert worker.run_once() == 2

        document = Document.objects.get(id=document_id)
        assert document.status == Document.Status.OCR_COMPLETED
        assert document.raw_text_uri.endswith("/ocr/raw_text.json")
        assert DocumentEvent.objects.count() == 2

    def test_worker_continues_after_invalid_event(self) -> None:
        event_dir = TemporaryDirectory()
        self.addCleanup(event_dir.cleanup)
        event_bus = LocalJsonlEventBus(event_dir.name)
        document_id = uuid4()
        event_bus.publish("ocr.completed", {"event_type": "ocr.completed", "document_id": str(document_id)})

        worker = CoreEventStreamWorker(event_bus=event_bus, start_at_latest=False)

        assert worker.run_once() == 0
        assert worker.offsets["ocr.completed"] == 1
