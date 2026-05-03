from __future__ import annotations

from uuid import uuid4
import json
import logging

from docuparse_events import LocalJsonlEventBus, RedisStreamEventBus, event_bus_from_env
from docuparse_observability import log_event
from docuparse_storage import LocalStorage, document_ocr_raw_text_key, document_original_key


def test_local_storage_roundtrip_and_uri_convention(tmp_path) -> None:
    tenant_id = "tenant-demo"
    document_id = str(uuid4())
    storage = LocalStorage(tmp_path)

    key = document_original_key(tenant_id, document_id)
    stored = storage.put_bytes(key, b"fake-pdf")

    assert stored.uri == f"local://documents/{tenant_id}/{document_id}/original"
    assert storage.get_bytes(stored.uri) == b"fake-pdf"
    assert document_ocr_raw_text_key(tenant_id, document_id) == (
        f"documents/{tenant_id}/{document_id}/ocr/raw_text.json"
    )


def test_local_event_bus_publish_and_consume_fake_document_received(tmp_path) -> None:
    bus = LocalJsonlEventBus(tmp_path)
    event = {
        "event_type": "document.received.fake",
        "document_id": str(uuid4()),
    }

    offset = bus.publish("document.received.fake", event)
    consumed = bus.consume("document.received.fake")
    entries = bus.consume_entries("document.received.fake")

    assert offset == 0
    assert consumed == [event]
    assert entries[0].id == 1
    assert entries[0].payload == event


def test_event_bus_from_env_defaults_to_local(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DOCUPARSE_EVENT_BUS", raising=False)
    monkeypatch.setenv("DOCUPARSE_LOCAL_EVENT_DIR", str(tmp_path / "events"))

    bus = event_bus_from_env()

    assert isinstance(bus, LocalJsonlEventBus)


def test_redis_stream_event_bus_publish_and_consume() -> None:
    client = FakeRedisStreams()
    bus = RedisStreamEventBus(client)
    event = {
        "event_type": "document.received.fake",
        "document_id": str(uuid4()),
    }

    event_id = bus.publish("document.received.fake", event)
    consumed = bus.consume("document.received.fake")
    entries = bus.consume_entries("document.received.fake")

    assert event_id == "1-0"
    assert consumed == [event]
    assert entries[0].id == "1-0"
    assert entries[0].payload == event


def test_log_event_emits_trace_context(caplog) -> None:
    logger = logging.getLogger("docuparse-test")

    with caplog.at_level(logging.INFO):
        log_event(
            logger,
            "document tracked",
            tenant_id="tenant-demo",
            document_id="doc-1",
            correlation_id="corr-1",
            event_type="document.received",
        )

    payload = json.loads(caplog.records[0].message)
    assert payload["tenant_id"] == "tenant-demo"
    assert payload["document_id"] == "doc-1"
    assert payload["correlation_id"] == "corr-1"
    assert payload["event_type"] == "document.received"


class FakeRedisStreams:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[bytes, bytes]]]] = {}

    def xadd(self, stream: str, fields: dict[str, str]) -> bytes:
        messages = self.streams.setdefault(stream, [])
        message_id = f"{len(messages) + 1}-0"
        encoded_fields = {
            key.encode("utf-8"): value.encode("utf-8")
            for key, value in fields.items()
        }
        messages.append((message_id, encoded_fields))
        return message_id.encode("utf-8")

    def xread(self, streams: dict[str, str], count: int | None = None) -> list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]]:
        output = []
        for stream, offset in streams.items():
            messages = [
                (message_id.encode("utf-8"), fields)
                for message_id, fields in self.streams.get(stream, [])
                if _redis_id_gt(message_id, offset)
            ]
            if count is not None:
                messages = messages[:count]
            if messages:
                output.append((stream.encode("utf-8"), messages))
        return output

    def xrevrange(self, stream: str, count: int | None = None) -> list[tuple[bytes, dict[bytes, bytes]]]:
        messages = list(reversed(self.streams.get(stream, [])))
        if count is not None:
            messages = messages[:count]
        return [(message_id.encode("utf-8"), fields) for message_id, fields in messages]


def _redis_id_gt(left: str, right: str) -> bool:
    left_ms, left_seq = [int(part) for part in left.split("-", 1)]
    right_ms, right_seq = [int(part) for part in right.split("-", 1)]
    return (left_ms, left_seq) > (right_ms, right_seq)
