from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from docuparse_events import EventBus


DEFAULT_DLQ_STREAMS = [
    "document.received.dlq",
    "ocr.completed.dlq",
    "ocr.failed.dlq",
    "layout.classified.dlq",
    "extraction.completed.dlq",
    "erp.sent.dlq",
    "erp.failed.dlq",
]

DEFAULT_REQUEUE_TARGETS = [stream.removesuffix(".dlq") for stream in DEFAULT_DLQ_STREAMS]


def inspect_dlq_streams(
    event_bus: EventBus,
    *,
    streams: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return [
        _inspect_stream(event_bus, stream, limit=max(limit, 0))
        for stream in (streams or DEFAULT_DLQ_STREAMS)
    ]


def requeue_dlq_entry(
    event_bus: EventBus,
    *,
    stream: str,
    entry_id: str,
    target_stream: str | None = None,
    note: str = "",
    requested_by: str = "system",
    execute: bool = False,
    limit: int = 500,
) -> dict[str, Any]:
    if stream not in DEFAULT_DLQ_STREAMS:
        raise ValueError(f"Invalid DLQ stream: {stream}")

    entry = _find_entry(event_bus, stream, entry_id, limit=limit)
    if entry is None:
        raise ValueError(f"DLQ entry not found: {stream}#{entry_id}")

    payload = entry.payload.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("DLQ entry does not contain a requeueable original payload")

    resolved_target = target_stream or entry.payload.get("stream") or stream.removesuffix(".dlq")
    if resolved_target not in DEFAULT_REQUEUE_TARGETS:
        raise ValueError(f"Invalid requeue target stream: {resolved_target}")

    result = {
        "execute": execute,
        "dlq_stream": stream,
        "dlq_entry_id": str(entry.id),
        "target_stream": resolved_target,
        "event_type": payload.get("event_type"),
        "event_id": payload.get("event_id"),
        "source": entry.payload.get("source"),
        "error_type": entry.payload.get("error_type"),
        "error": entry.payload.get("error"),
        "requeued_event_stream_id": None,
        "audit_event_stream_id": None,
    }

    if not execute:
        return result

    result["requeued_event_stream_id"] = str(event_bus.publish(resolved_target, payload))
    result["audit_event_stream_id"] = str(
        event_bus.publish(
            f"{stream}.requeued",
            {
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "dlq_stream": stream,
                "dlq_entry_id": str(entry.id),
                "target_stream": resolved_target,
                "requeued_event_stream_id": result["requeued_event_stream_id"],
                "requested_by": requested_by,
                "note": note,
                "payload_event_type": payload.get("event_type"),
                "payload_event_id": payload.get("event_id"),
            },
        )
    )
    return result


def _inspect_stream(event_bus: EventBus, stream: str, *, limit: int) -> dict[str, Any]:
    entries = event_bus.consume_entries(stream, 0, count=limit)
    return {
        "stream": stream,
        "count": len(entries),
        "entries": [
            {
                "id": str(entry.id),
                "event_id": entry.payload.get("event_id"),
                "event_type": entry.payload.get("event_type"),
                "source": entry.payload.get("source"),
                "error_type": entry.payload.get("error_type"),
                "error": entry.payload.get("error"),
                "payload": entry.payload.get("payload"),
                "occurred_at": entry.payload.get("occurred_at"),
                "original_stream": entry.payload.get("stream"),
                "event_stream_id": entry.payload.get("event_stream_id"),
            }
            for entry in entries
        ],
    }


def _find_entry(event_bus: EventBus, stream: str, entry_id: str, *, limit: int):
    for entry in event_bus.consume_entries(stream, 0, count=max(limit, 1)):
        if str(entry.id) == str(entry_id):
            return entry
    return None
