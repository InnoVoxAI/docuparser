from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class EventMessage:
    id: int | str
    payload: dict[str, Any]


class EventBus(Protocol):
    def publish(self, stream: str, event: dict[str, Any]) -> int | str:
        ...

    def consume(self, stream: str, offset: int | str = 0) -> list[dict[str, Any]]:
        ...

    def consume_entries(self, stream: str, offset: int | str = 0, count: int | None = None) -> list[EventMessage]:
        ...


class LocalJsonlEventBus:
    """Small test adapter that mimics append-only event streams on disk."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, stream: str, event: dict[str, Any]) -> int:
        path = self._stream_path(stream)
        next_offset = self._count(path)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, separators=(",", ":"), default=str))
            file.write("\n")
        return next_offset

    def consume(self, stream: str, offset: int = 0) -> list[dict[str, Any]]:
        return [entry.payload for entry in self.consume_entries(stream, offset)]

    def consume_entries(self, stream: str, offset: int | str = 0, count: int | None = None) -> list[EventMessage]:
        path = self._stream_path(stream)
        if not path.exists():
            return []
        start = 0 if isinstance(offset, str) and "-" in offset else int(offset)
        lines = path.read_text(encoding="utf-8").splitlines()[start:]
        if count is not None:
            lines = lines[:count]
        events: list[EventMessage] = []
        for index, line in enumerate(lines, start=start):
            if line.strip():
                events.append(EventMessage(id=index + 1, payload=json.loads(line)))
        return events

    def _stream_path(self, stream: str) -> Path:
        validate_stream_name(stream)
        return self.root / f"{stream}.jsonl"

    @staticmethod
    def _count(path: Path) -> int:
        if not path.exists():
            return 0
        return len(path.read_text(encoding="utf-8").splitlines())


class RedisStreamEventBus:
    """Redis Streams adapter used by the integrated docker environment."""

    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisStreamEventBus":
        try:
            import redis
        except ModuleNotFoundError as exc:
            raise RuntimeError("Redis event bus requires the 'redis' Python package") from exc
        return cls(redis.Redis.from_url(url))

    def publish(self, stream: str, event: dict[str, Any]) -> str:
        validate_stream_name(stream)
        payload = json.dumps(event, separators=(",", ":"), default=str)
        event_id = self.client.xadd(stream, {"payload": payload})
        return _decode(event_id)

    def consume(self, stream: str, offset: int | str = "0-0", count: int | None = None) -> list[dict[str, Any]]:
        return [entry.payload for entry in self.consume_entries(stream, offset, count)]

    def consume_entries(self, stream: str, offset: int | str = "0-0", count: int | None = None) -> list[EventMessage]:
        validate_stream_name(stream)
        redis_offset = "0-0" if offset == 0 else str(offset)
        response = self.client.xread({stream: redis_offset}, count=count)
        events: list[EventMessage] = []
        for _stream_name, messages in response:
            for message_id, fields in messages:
                payload = _field(fields, "payload")
                if payload:
                    events.append(EventMessage(id=_decode(message_id), payload=json.loads(payload)))
        return events

    def latest_id(self, stream: str) -> str:
        validate_stream_name(stream)
        response = self.client.xrevrange(stream, count=1)
        if not response:
            return "0-0"
        return _decode(response[0][0])


def event_bus_from_env(local_root: str | Path | None = None) -> EventBus:
    mode = os.environ.get("DOCUPARSE_EVENT_BUS", "local").strip().lower()
    if mode in {"redis", "redis-streams", "redis_streams"}:
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0").strip()
        return RedisStreamEventBus.from_url(redis_url)
    root = local_root or os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", ".docuparse-events")
    return LocalJsonlEventBus(root)


def publish_dead_letter(
    event_bus: EventBus,
    *,
    stream: str,
    entry: EventMessage,
    error: BaseException,
    source: str,
) -> int | str:
    return event_bus.publish(
        f"{stream}.dlq",
        {
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "stream": stream,
            "event_stream_id": str(entry.id),
            "event_type": entry.payload.get("event_type"),
            "event_id": entry.payload.get("event_id"),
            "error_type": type(error).__name__,
            "error": str(error),
            "payload": entry.payload,
        },
    )


def validate_stream_name(stream: str) -> None:
    if "/" in stream or ".." in stream or not stream.strip():
        raise ValueError(f"Invalid stream name: {stream!r}")


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _field(fields: dict[Any, Any], name: str) -> str:
    value = fields.get(name)
    if value is None:
        value = fields.get(name.encode("utf-8"))
    return _decode(value) if value is not None else ""


def sleep_interval(seconds: float) -> None:
    time.sleep(max(seconds, 0.0))
