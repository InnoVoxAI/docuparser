from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from domain.classifier import classify_layout
from events import LayoutClassifiedEvent, OCRCompletedEvent
from docuparse_events import EventBus, event_bus_from_env, sleep_interval
from docuparse_observability import log_event
from docuparse_storage import LocalStorage

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def get_bytes(self, uri_or_key: str) -> bytes:
        ...


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int | str:
        ...


def handle_ocr_completed_event(
    payload: dict[str, Any],
    storage: Storage,
    publisher: EventPublisher,
    *,
    source: str = "layout-service",
) -> dict[str, Any]:
    event = OCRCompletedEvent.model_validate(payload)
    raw_payload = json.loads(storage.get_bytes(event.data.raw_text_uri).decode("utf-8"))
    raw_text = str(raw_payload.get("raw_text", ""))
    document_type = str(raw_payload.get("document_type") or event.data.document_type)

    classification = classify_layout(raw_text, document_type)
    output = LayoutClassifiedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        tenant_id=event.tenant_id,
        document_id=event.document_id,
        correlation_id=event.correlation_id,
        source=source,
        data={
            "layout": classification.layout,
            "confidence": classification.confidence,
            "document_type": document_type,
            "requires_human_validation": classification.requires_human_validation,
            "metadata": {
                "input_event_id": str(event.event_id),
                "raw_text_uri": event.data.raw_text_uri,
            },
        },
    ).model_dump(mode="json")
    publisher.publish("layout.classified", output)
    log_event(
        logger,
        "layout.classified published",
        tenant_id=event.tenant_id,
        document_id=str(event.document_id),
        correlation_id=str(event.correlation_id),
        event_type="layout.classified",
        layout=classification.layout,
        confidence=classification.confidence,
    )
    return output


class LayoutWorker:
    def __init__(
        self,
        *,
        storage: Storage,
        event_bus: EventBus,
        input_stream: str = "ocr.completed",
        poll_interval_seconds: float = 2.0,
        start_at_latest: bool = True,
    ) -> None:
        self.storage = storage
        self.event_bus = event_bus
        self.input_stream = input_stream
        self.poll_interval_seconds = poll_interval_seconds
        self._stop = threading.Event()
        self._offset: int | str = self._initial_offset(start_at_latest)

    def stop(self) -> None:
        self._stop.set()

    def run_forever(self) -> None:
        logger.info("Layout Redis worker started", extra={"stream": self.input_stream, "offset": self._offset})
        while not self._stop.is_set():
            processed = self.run_once()
            if processed == 0:
                sleep_interval(self.poll_interval_seconds)

    def run_once(self) -> int:
        entries = self.event_bus.consume_entries(self.input_stream, self._offset, count=10)
        for entry in entries:
            try:
                handle_ocr_completed_event(entry.payload, self.storage, self.event_bus)
            except Exception:
                log_event(
                    logger,
                    "layout event processing failed",
                    level=logging.ERROR,
                    stream=self.input_stream,
                    event_stream_id=str(entry.id),
                    event_type=entry.payload.get("event_type"),
                    event_id=entry.payload.get("event_id"),
                )
            finally:
                self._offset = entry.id
        return len(entries)

    def _initial_offset(self, start_at_latest: bool) -> int | str:
        if not start_at_latest:
            return "0-0"
        latest_id = getattr(self.event_bus, "latest_id", None)
        if callable(latest_id):
            return latest_id(self.input_stream)
        entries = self.event_bus.consume_entries(self.input_stream)
        return entries[-1].id if entries else 0


def worker_from_env() -> LayoutWorker:
    storage_root = os.environ.get("DOCUPARSE_LOCAL_STORAGE_DIR", "/data/storage")
    return LayoutWorker(
        storage=LocalStorage(storage_root),
        event_bus=event_bus_from_env(os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", "/data/events")),
        input_stream=os.environ.get("DOCUPARSE_LAYOUT_INPUT_STREAM", "ocr.completed"),
        poll_interval_seconds=float(os.environ.get("DOCUPARSE_LAYOUT_WORKER_POLL_SECONDS", "2")),
        start_at_latest=os.environ.get("DOCUPARSE_LAYOUT_WORKER_START_AT_LATEST", "true").strip().lower()
        not in {"0", "false", "no"},
    )


def start_worker_thread_from_env() -> LayoutWorker | None:
    enabled = os.environ.get("DOCUPARSE_LAYOUT_WORKER_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        return None
    worker = worker_from_env()
    thread = threading.Thread(target=worker.run_forever, name="docuparse-layout-worker", daemon=True)
    thread.start()
    return worker
