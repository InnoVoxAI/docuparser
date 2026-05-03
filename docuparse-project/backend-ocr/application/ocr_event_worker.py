from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

from events import DocumentReceivedEvent, OCRCompletedEvent, OCRFailedEvent
from docuparse_observability import log_event

from application.process_document import process_document

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def get_bytes(self, uri_or_key: str) -> bytes:
        ...

    def put_bytes(self, key: str, content: bytes):
        ...


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int:
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
        result = process_document(
            file_bytes=file_bytes,
            filename=event.data.file.filename,
            timeout_s=int(event.data.metadata.get("timeout_s", 120)),
            legacy_extraction=False,
        )

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
