from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from domain.backend_core_client import fetch_schema_for_layout
from domain.extractor import extract_fields
from domain.llm_extractor import extract_with_llm
from events import ExtractionCompletedEvent, LayoutClassifiedEvent
from docuparse_events import EventBus, event_bus_from_env, publish_dead_letter, sleep_interval
from docuparse_observability import log_event
from docuparse_storage import LocalStorage

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def get_bytes(self, uri_or_key: str) -> bytes:
        ...


class EventPublisher(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int | str:
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

    # --- Extraction strategy selection ---
    # 1. Try to load the SchemaConfig definition linked to this layout in backend-core.
    # 2. If found: use the LLM extractor with the full prompt + field list from the schema.
    # 3. If not found (no config, service unreachable, etc.): fall back to the legacy
    #    regex-based extractor so existing layouts keep working unchanged.
    schema_definition, confidence_threshold = fetch_schema_for_layout(
        tenant_id=event.tenant_id,
        layout=event.data.layout,
        document_type=event.data.document_type,
    )

    if schema_definition:
        log_event(
            logger,
            "langextract.using_llm_extraction",
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            layout=event.data.layout,
            schema_id=schema_definition.get("schema_id"),
        )
        extracted = extract_with_llm(
            raw_text,
            schema_definition,
            tenant_id=event.tenant_id,
            confidence_threshold=confidence_threshold,
        )
    else:
        log_event(
            logger,
            "langextract.using_regex_extraction",
            tenant_id=event.tenant_id,
            document_id=str(event.document_id),
            layout=event.data.layout,
        )
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


class ExtractionWorker:
    def __init__(
        self,
        *,
        storage: Storage,
        event_bus: EventBus,
        input_stream: str = "layout.classified",
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
        logger.info("LangExtract Redis worker started", extra={"stream": self.input_stream, "offset": self._offset})
        while not self._stop.is_set():
            processed = self.run_once()
            if processed == 0:
                sleep_interval(self.poll_interval_seconds)

    def run_once(self) -> int:
        entries = self.event_bus.consume_entries(self.input_stream, self._offset, count=10)
        for entry in entries:
            try:
                handle_layout_classified_event(entry.payload, self.storage, self.event_bus)
            except Exception as exc:
                publish_dead_letter(
                    self.event_bus,
                    stream=self.input_stream,
                    entry=entry,
                    error=exc,
                    source="langextract-service",
                )
                log_event(
                    logger,
                    "extraction event processing failed",
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


def worker_from_env() -> ExtractionWorker:
    storage_root = os.environ.get("DOCUPARSE_LOCAL_STORAGE_DIR", "/data/storage")
    return ExtractionWorker(
        storage=LocalStorage(storage_root),
        event_bus=event_bus_from_env(os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", "/data/events")),
        input_stream=os.environ.get("DOCUPARSE_EXTRACTION_INPUT_STREAM", "layout.classified"),
        poll_interval_seconds=float(os.environ.get("DOCUPARSE_EXTRACTION_WORKER_POLL_SECONDS", "2")),
        start_at_latest=os.environ.get("DOCUPARSE_EXTRACTION_WORKER_START_AT_LATEST", "true").strip().lower()
        not in {"0", "false", "no"},
    )


def start_worker_thread_from_env() -> ExtractionWorker | None:
    enabled = os.environ.get("DOCUPARSE_EXTRACTION_WORKER_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        return None
    worker = worker_from_env()
    thread = threading.Thread(target=worker.run_forever, name="docuparse-extraction-worker", daemon=True)
    thread.start()
    return worker
