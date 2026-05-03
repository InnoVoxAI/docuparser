from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from domain.classifier import classify_layout
from events import LayoutClassifiedEvent, OCRCompletedEvent
from docuparse_observability import log_event

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def get_bytes(self, uri_or_key: str) -> bytes:
        ...


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int:
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
