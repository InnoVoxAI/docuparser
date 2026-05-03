from __future__ import annotations

import json
from io import StringIO
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from docuparse_events import EventMessage, LocalJsonlEventBus, publish_dead_letter


class InspectDLQCommandTests(TestCase):
    def test_inspect_dlq_outputs_summary_for_known_stream(self) -> None:
        event_dir = TemporaryDirectory()
        self.addCleanup(event_dir.cleanup)
        bus = LocalJsonlEventBus(event_dir.name)
        publish_dead_letter(
            bus,
            stream="ocr.completed",
            entry=EventMessage(id=1, payload={"event_type": "ocr.completed", "event_id": "event-1"}),
            error=ValueError("invalid event"),
            source="backend-core",
        )
        output = StringIO()

        with self.settings(DOCUPARSE_LOCAL_EVENT_DIR=event_dir.name):
            call_command("inspect_dlq", "--stream", "ocr.completed.dlq", "--summary", stdout=output)

        assert "ocr.completed.dlq: 1" in output.getvalue()

    def test_inspect_dlq_can_emit_json(self) -> None:
        event_dir = TemporaryDirectory()
        self.addCleanup(event_dir.cleanup)
        bus = LocalJsonlEventBus(event_dir.name)
        publish_dead_letter(
            bus,
            stream="layout.classified",
            entry=EventMessage(id=2, payload={"event_type": "layout.classified", "event_id": "event-2"}),
            error=RuntimeError("missing raw text"),
            source="langextract-service",
        )
        output = StringIO()

        with self.settings(DOCUPARSE_LOCAL_EVENT_DIR=event_dir.name):
            call_command("inspect_dlq", "--stream", "layout.classified.dlq", "--json", stdout=output)

        data = json.loads(output.getvalue())
        assert data[0]["stream"] == "layout.classified.dlq"
        assert data[0]["count"] == 1
        assert data[0]["entries"][0]["error_type"] == "RuntimeError"

    def test_requeue_dlq_dry_run_does_not_publish_original_payload(self) -> None:
        event_dir = TemporaryDirectory()
        self.addCleanup(event_dir.cleanup)
        bus = LocalJsonlEventBus(event_dir.name)
        publish_dead_letter(
            bus,
            stream="ocr.completed",
            entry=EventMessage(id=3, payload={"event_type": "ocr.completed", "event_id": "event-3"}),
            error=ValueError("invalid event"),
            source="backend-core",
        )
        output = StringIO()

        with self.settings(DOCUPARSE_LOCAL_EVENT_DIR=event_dir.name):
            call_command("requeue_dlq", "--stream", "ocr.completed.dlq", "--id", "1", stdout=output)

        assert "DRY-RUN ocr.completed.dlq#1 -> ocr.completed" in output.getvalue()
        assert bus.consume("ocr.completed") == []

    def test_requeue_dlq_execute_publishes_original_payload_and_audit_event(self) -> None:
        event_dir = TemporaryDirectory()
        self.addCleanup(event_dir.cleanup)
        bus = LocalJsonlEventBus(event_dir.name)
        publish_dead_letter(
            bus,
            stream="layout.classified",
            entry=EventMessage(id=4, payload={"event_type": "layout.classified", "event_id": "event-4"}),
            error=RuntimeError("missing schema"),
            source="langextract-service",
        )
        output = StringIO()

        with self.settings(DOCUPARSE_LOCAL_EVENT_DIR=event_dir.name):
            call_command(
                "requeue_dlq",
                "--stream",
                "layout.classified.dlq",
                "--id",
                "1",
                "--execute",
                "--note",
                "reviewed",
                stdout=output,
            )

        assert "REQUEUED layout.classified.dlq#1 -> layout.classified" in output.getvalue()
        assert bus.consume("layout.classified")[0]["event_id"] == "event-4"
        audit = bus.consume("layout.classified.dlq.requeued")
        assert audit[0]["dlq_entry_id"] == "1"
        assert audit[0]["note"] == "reviewed"
