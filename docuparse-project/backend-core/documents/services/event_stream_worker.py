from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from docuparse_events import EventBus, sleep_interval
from docuparse_observability import log_event

from documents.services.event_consumers import (
    consume_document_received,
    consume_erp_failed,
    consume_erp_sent,
    consume_extraction_completed,
    consume_ocr_completed,
    consume_ocr_failed,
)

logger = logging.getLogger(__name__)

EventConsumer = Callable[[dict[str, Any]], Any]

CORE_EVENT_CONSUMERS: dict[str, EventConsumer] = {
    "document.received": consume_document_received,
    "ocr.completed": consume_ocr_completed,
    "ocr.failed": consume_ocr_failed,
    "extraction.completed": consume_extraction_completed,
    "erp.sent": consume_erp_sent,
    "erp.failed": consume_erp_failed,
}


@dataclass
class CoreEventStreamWorker:
    event_bus: EventBus
    consumers: dict[str, EventConsumer] = field(default_factory=lambda: dict(CORE_EVENT_CONSUMERS))
    poll_seconds: float = 1.0
    batch_size: int = 25
    start_at_latest: bool = True
    offsets: dict[str, int | str] = field(default_factory=dict)
    _running: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for stream in self.consumers:
            self.offsets.setdefault(stream, self._initial_offset(stream))

    def run_once(self) -> int:
        processed_count = 0
        for stream, consumer in self.consumers.items():
            entries = self.event_bus.consume_entries(stream, self.offsets[stream], count=self.batch_size)
            for entry in entries:
                try:
                    consumer(entry.payload)
                    processed_count += 1
                except Exception:
                    log_event(
                        logger,
                        "core event stream processing failed",
                        level=logging.ERROR,
                        stream=stream,
                        event_stream_id=str(entry.id),
                        event_type=entry.payload.get("event_type"),
                        event_id=entry.payload.get("event_id"),
                    )
                finally:
                    self.offsets[stream] = entry.id
        return processed_count

    def run_forever(self) -> None:
        self._running = True
        log_event(
            logger,
            "core event stream worker started",
            streams=list(self.consumers),
            poll_seconds=self.poll_seconds,
        )
        while self._running:
            processed_count = self.run_once()
            if processed_count == 0:
                sleep_interval(self.poll_seconds)

    def stop(self) -> None:
        self._running = False

    def _initial_offset(self, stream: str) -> int | str:
        if not self.start_at_latest:
            return "0-0"
        latest_id = getattr(self.event_bus, "latest_id", None)
        if callable(latest_id):
            return latest_id(stream)
        entries = self.event_bus.consume_entries(stream, 0)
        return entries[-1].id if entries else 0
