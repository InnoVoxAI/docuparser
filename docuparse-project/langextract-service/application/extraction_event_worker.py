from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from domain.extractor import extract_fields
from events import ExtractionCompletedEvent, LayoutClassifiedEvent
from docuparse_observability import log_event

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def get_bytes(self, uri_or_key: str) -> bytes:
        ...


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int:
        ...


def handle_layout_classified_event(
    payload: dict[str, Any],
    storage: Storage,
    publisher: EventPublisher,
    *,
    source: str = "langextract-service",
) -> dict[str, Any]:
    event = LayoutClassifiedEvent.model_validate(payload)
    raw_text_uri = str(event.data.metadata.get("raw_text_uri", ""))
    raw_payload = json.loads(storage.get_bytes(raw_text_uri).decode("utf-8"))
    raw_text = str(raw_payload.get("raw_text", ""))

    extracted = extract_fields(raw_text, event.data.layout, event.data.document_type)
    output = ExtractionCompletedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        tenant_id=event.tenant_id,
        document_id=event.document_id,
        correlation_id=event.correlation_id,
        source=source,
        data={
            "schema_id": extracted.schema_id,
            "schema_version": extracted.schema_version,
            "fields": extracted.fields,
            "confidence": extracted.confidence,
            "requires_human_validation": extracted.requires_human_validation,
            "metadata": {
                "input_event_id": str(event.event_id),
                "layout": event.data.layout,
                "raw_text_uri": raw_text_uri,
            },
        },
    ).model_dump(mode="json")
    publisher.publish("extraction.completed", output)
    log_event(
        logger,
        "extraction.completed published",
        tenant_id=event.tenant_id,
        document_id=str(event.document_id),
        correlation_id=str(event.correlation_id),
        event_type="extraction.completed",
        schema_id=extracted.schema_id,
        confidence=extracted.confidence,
    )
    return output
