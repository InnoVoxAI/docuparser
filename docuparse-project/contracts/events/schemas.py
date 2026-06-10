from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


EVENT_VERSION = "v1"


class EventModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseEvent(EventModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: Literal["v1"] = EVENT_VERSION
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str = Field(min_length=1)
    document_id: UUID
    correlation_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=1)

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include timezone information")
        return value


class FileRef(EventModel):
    uri: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class DocumentReceivedData(EventModel):
    channel: Literal["manual", "email", "whatsapp"]
    file: FileRef
    received_at: datetime
    sender: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentReceivedEvent(BaseEvent):
    event_type: Literal["document.received"] = "document.received"
    data: DocumentReceivedData


class OCRCompletedData(EventModel):
    raw_text_uri: str = Field(min_length=1)
    raw_text_preview: str = ""
    document_type: Literal["digital_pdf", "scanned_image", "handwritten_complex", "unknown"]
    engine_used: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    processing_time_seconds: float = Field(ge=0.0)
    artifacts: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OCRCompletedEvent(BaseEvent):
    event_type: Literal["ocr.completed"] = "ocr.completed"
    data: OCRCompletedData


class OCRFailedData(EventModel):
    reason: str = Field(min_length=1)
    retryable: bool = True
    engine_used: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OCRFailedEvent(BaseEvent):
    event_type: Literal["ocr.failed"] = "ocr.failed"
    data: OCRFailedData


class LayoutClassifiedData(EventModel):
    layout: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    document_type: str = Field(min_length=1)
    requires_human_validation: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayoutClassifiedEvent(BaseEvent):
    event_type: Literal["layout.classified"] = "layout.classified"
    data: LayoutClassifiedData


class ExtractionCompletedData(EventModel):
    schema_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    fields: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_validation: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractionCompletedEvent(BaseEvent):
    event_type: Literal["extraction.completed"] = "extraction.completed"
    data: ExtractionCompletedData


class ERPIntegrationRequestedData(EventModel):
    connector: str = Field(min_length=1)
    payload: dict[str, Any]
    idempotency_key: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ERPIntegrationRequestedEvent(BaseEvent):
    event_type: Literal["erp.integration.requested"] = "erp.integration.requested"
    data: ERPIntegrationRequestedData


class ERPSentData(EventModel):
    connector: str = Field(min_length=1)
    external_id: str | None = None
    idempotency_key: str = Field(min_length=1)
    response_metadata: dict[str, Any] = Field(default_factory=dict)


class ERPSentEvent(BaseEvent):
    event_type: Literal["erp.sent"] = "erp.sent"
    data: ERPSentData


class ERPFailedData(EventModel):
    connector: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    retryable: bool
    idempotency_key: str = Field(min_length=1)
    response_metadata: dict[str, Any] = Field(default_factory=dict)


class ERPFailedEvent(BaseEvent):
    event_type: Literal["erp.failed"] = "erp.failed"
    data: ERPFailedData


EVENT_MODELS = {
    "document.received": DocumentReceivedEvent,
    "ocr.completed": OCRCompletedEvent,
    "ocr.failed": OCRFailedEvent,
    "layout.classified": LayoutClassifiedEvent,
    "extraction.completed": ExtractionCompletedEvent,
    "erp.integration.requested": ERPIntegrationRequestedEvent,
    "erp.sent": ERPSentEvent,
    "erp.failed": ERPFailedEvent,
}


def validate_event(payload: dict[str, Any]) -> BaseEvent:
    event_type = payload.get("event_type")
    try:
        model = EVENT_MODELS[event_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported event_type: {event_type}") from exc
    return model.model_validate(payload)
