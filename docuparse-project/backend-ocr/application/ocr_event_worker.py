from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

from events import DocumentReceivedEvent, OCRCompletedEvent, OCRFailedEvent
from docuparse_events import EventBus, event_bus_from_env, sleep_interval
from docuparse_observability import log_event
from docuparse_storage import LocalStorage

from application.process_document import process_document

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def get_bytes(self, uri_or_key: str) -> bytes:
        ...

    def put_bytes(self, key: str, content: bytes):
        ...


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int | str:
        ...


def raw_text_key(tenant_id: str, document_id: UUID) -> str:
    return f"documents/{tenant_id}/{document_id}/ocr/raw_text.json"


def handle_document_received_event(
    payload: dict[str, Any],
    storage: Storage,
    publisher: EventPublisher,
    *,
    source: str = "backend-ocr",
) -> dict[str, Any]:
    event = DocumentReceivedEvent.model_validate(payload)

    try:
        file_bytes = storage.get_bytes(event.data.file.uri)
        result = _process_or_mock_document(event, file_bytes)

        raw_payload = {
            "raw_text": result.get("raw_text", ""),
            "raw_text_fallback": result.get("raw_text_fallback", ""),
            "document_type": result.get("document_type", "unknown"),
            "engine_used": result.get("engine_used", "unknown"),
            "processing_time_seconds": result.get("processing_time_seconds", 0.0),
            "metadata": {
                "filename": result.get("filename"),
                "debug": result.get("debug", {}),
            },
        }
        stored = storage.put_bytes(
            raw_text_key(event.tenant_id, event.document_id),
            json.dumps(raw_payload, ensure_ascii=False).encode("utf-8"),
        )

        completed = OCRCompletedEvent(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            tenant_id=event.tenant_id,
            document_id=event.document_id,
            correlation_id=event.correlation_id,
            source=source,
            data={
                "raw_text_uri": stored.uri,
                "raw_text_preview": str(result.get("raw_text", ""))[:500],
                "document_type": result.get("document_type", "unknown"),
                "engine_used": result.get("engine_used", "unknown"),
                "confidence": None,
                "processing_time_seconds": result.get("processing_time_seconds", 0.0),
                "artifacts": {},
                "metadata": {
                    "input_event_id": str(event.event_id),
                    "raw_text_sha256": stored.sha256,
                    "raw_text_size_bytes": stored.size_bytes,
                },
            },
        )
        event_dict = completed.model_dump(mode="json")
        publisher.publish("ocr.completed", event_dict)
        log_event(
            logger,
            "ocr.completed published",
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            correlation_id=str(event.correlation_id),
            event_type="ocr.completed",
            raw_text_uri=stored.uri,
        )
        return event_dict
    except Exception as exc:
        failed = OCRFailedEvent(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            tenant_id=event.tenant_id,
            document_id=event.document_id,
            correlation_id=event.correlation_id,
            source=source,
            data={
                "reason": str(exc),
                "retryable": True,
                "engine_used": None,
                "metadata": {
                    "input_event_id": str(event.event_id),
                    "file_uri": event.data.file.uri,
                },
            },
        )
        event_dict = failed.model_dump(mode="json")
        publisher.publish("ocr.failed", event_dict)
        log_event(
            logger,
            "ocr.failed published",
            level=logging.ERROR,
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            correlation_id=str(event.correlation_id),
            event_type="ocr.failed",
            reason=str(exc),
        )
        return event_dict


def _process_or_mock_document(event: DocumentReceivedEvent, file_bytes: bytes) -> dict[str, Any]:
    if _mock_ocr_allowed() and "ocr_mock_raw_text" in event.data.metadata:
        return {
            "raw_text": str(event.data.metadata.get("ocr_mock_raw_text", "")),
            "raw_text_fallback": "",
            "document_type": str(event.data.metadata.get("ocr_mock_document_type", "digital_pdf")),
            "engine_used": "mock",
            "processing_time_seconds": 0.0,
            "filename": event.data.file.filename,
            "debug": {
                "mock": True,
                "input_size_bytes": len(file_bytes),
            },
        }

    return process_document(
        file_bytes=file_bytes,
        filename=event.data.file.filename,
        timeout_s=int(event.data.metadata.get("timeout_s", 120)),
        legacy_extraction=False,
    )


def _mock_ocr_allowed() -> bool:
    return os.environ.get("DOCUPARSE_OCR_WORKER_ALLOW_MOCK", "").strip().lower() in {"1", "true", "yes"}


class OCRWorker:
    def __init__(
        self,
        *,
        storage: Storage,
        event_bus: EventBus,
        input_stream: str = "document.received",
        poll_interval_seconds: float = 2.0,
        start_at_latest: bool = True,
    ) -> None:
        self.storage = storage
        self.event_bus = event_bus
        self.input_stream = input_stream
        self.poll_interval_seconds = poll_interval_seconds
        self._stop = threading.Event()
        self._offset: int | str = self._initial_offset(start_at_latest)

    def _initial_offset(self, start_at_latest: bool) -> int | str:
        if not start_at_latest:
            return "0-0"
        latest_id = getattr(self.event_bus, "latest_id", None)
        if callable(latest_id):
            return latest_id(self.input_stream)
        entries = self.event_bus.consume_entries(self.input_stream)
        return entries[-1].id if entries else 0

    def stop(self) -> None:
        self._stop.set()

    def run_forever(self) -> None:
        logger.info("OCR Redis worker started", extra={"stream": self.input_stream, "offset": self._offset})
        while not self._stop.is_set():
            processed = self.run_once()
            if processed == 0:
                sleep_interval(self.poll_interval_seconds)

    def run_once(self) -> int:
        entries = self.event_bus.consume_entries(self.input_stream, self._offset, count=10)
        for entry in entries:
            self._offset = entry.id
            handle_document_received_event(entry.payload, self.storage, self.event_bus)
        return len(entries)


def worker_from_env() -> OCRWorker:
    storage_root = os.environ.get("DOCUPARSE_LOCAL_STORAGE_DIR", "/data/storage")
    return OCRWorker(
        storage=LocalStorage(storage_root),
        event_bus=event_bus_from_env(os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", "/data/events")),
        input_stream=os.environ.get("DOCUPARSE_OCR_INPUT_STREAM", "document.received"),
        poll_interval_seconds=float(os.environ.get("DOCUPARSE_OCR_WORKER_POLL_SECONDS", "2")),
        start_at_latest=os.environ.get("DOCUPARSE_OCR_WORKER_START_AT_LATEST", "true").strip().lower() not in {"0", "false", "no"},
    )


def start_worker_thread_from_env() -> OCRWorker | None:
    enabled = os.environ.get("DOCUPARSE_OCR_WORKER_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        return None
    worker = worker_from_env()
    thread = threading.Thread(target=worker.run_forever, name="docuparse-ocr-worker", daemon=True)
    thread.start()
    return worker
