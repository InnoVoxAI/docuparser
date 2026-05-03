from __future__ import annotations

from uuid import uuid4
import json
import logging

from docuparse_events import LocalJsonlEventBus
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

    assert offset == 0
    assert consumed == [event]


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
