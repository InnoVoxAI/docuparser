from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from application import ocr_event_worker
from docuparse_events import LocalJsonlEventBus
from docuparse_storage import LocalStorage, document_original_key
from events import validate_event


def _document_received_payload(storage: LocalStorage, tenant_id: str, document_id) -> dict:
    stored = storage.put_bytes(document_original_key(tenant_id, str(document_id)), b"document-bytes")
    return {
        "event_id": str(uuid4()),
        "event_type": "document.received",
        "event_version": "v1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "document_id": str(document_id),
        "correlation_id": str(uuid4()),
        "source": "backend-com",
        "data": {
            "channel": "manual",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "sender": "operator@example.test",
            "file": {
                "uri": stored.uri,
                "content_type": "application/pdf",
                "filename": "fixture.pdf",
                "size_bytes": stored.size_bytes,
                "sha256": stored.sha256,
            },
            "metadata": {},
        },
    }


def test_document_received_becomes_ocr_completed(monkeypatch, tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    publisher = LocalJsonlEventBus(tmp_path / "events")
    tenant_id = "tenant-demo"
    document_id = uuid4()
    payload = _document_received_payload(storage, tenant_id, document_id)

    def fake_process_document(file_bytes, filename, timeout_s=120, legacy_extraction=False, selected_engine=None):
        assert file_bytes == b"document-bytes"
        assert legacy_extraction is False
        return {
            "raw_text": "texto bruto",
            "raw_text_fallback": "",
            "document_type": "scanned_image",
            "engine_used": "mock",
            "processing_time_seconds": 0.01,
            "filename": filename,
            "debug": {},
        }

    monkeypatch.setattr(ocr_event_worker, "process_document", fake_process_document)

    output = ocr_event_worker.handle_document_received_event(payload, storage, publisher)

    validated = validate_event(output)
    assert validated.event_type == "ocr.completed"
    assert output["data"]["raw_text_uri"] == f"local://documents/{tenant_id}/{document_id}/ocr/raw_text.json"
    assert b"texto bruto" in storage.get_bytes(output["data"]["raw_text_uri"])
    assert publisher.consume("ocr.completed") == [output]


def test_document_received_failure_publishes_ocr_failed(monkeypatch, tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    publisher = LocalJsonlEventBus(tmp_path / "events")
    payload = _document_received_payload(storage, "tenant-demo", uuid4())

    def failing_process_document(**kwargs):
        raise RuntimeError("OCR unavailable")

    monkeypatch.setattr(ocr_event_worker, "process_document", failing_process_document)

    output = ocr_event_worker.handle_document_received_event(payload, storage, publisher)

    validated = validate_event(output)
    assert validated.event_type == "ocr.failed"
    assert output["data"]["reason"] == "OCR unavailable"
    assert publisher.consume("ocr.failed") == [output]


def test_ocr_worker_consumes_document_received_stream(monkeypatch, tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    event_bus = LocalJsonlEventBus(tmp_path / "events")
    tenant_id = "tenant-demo"
    document_id = uuid4()
    payload = _document_received_payload(storage, tenant_id, document_id)
    event_bus.publish("document.received", payload)

    def fake_process_document(file_bytes, filename, timeout_s=120, legacy_extraction=False, selected_engine=None):
        return {
            "raw_text": "texto do worker",
            "raw_text_fallback": "",
            "document_type": "digital_pdf",
            "engine_used": "docling",
            "processing_time_seconds": 0.01,
            "filename": filename,
            "debug": {},
        }

    monkeypatch.setattr(ocr_event_worker, "process_document", fake_process_document)
    worker = ocr_event_worker.OCRWorker(
        storage=storage,
        event_bus=event_bus,
        input_stream="document.received",
        start_at_latest=False,
    )

    processed = worker.run_once()

    assert processed == 1
    completed = event_bus.consume("ocr.completed")
    assert len(completed) == 1
    assert completed[0]["data"]["engine_used"] == "docling"


def test_ocr_worker_can_use_explicit_mock_mode(monkeypatch, tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    event_bus = LocalJsonlEventBus(tmp_path / "events")
    tenant_id = "tenant-demo"
    document_id = uuid4()
    payload = _document_received_payload(storage, tenant_id, document_id)
    payload["data"]["metadata"] = {
        "ocr_mock_raw_text": "Banco do Brasil Valor R$ 123,45",
        "ocr_mock_document_type": "digital_pdf",
    }
    event_bus.publish("document.received", payload)
    monkeypatch.setenv("DOCUPARSE_OCR_WORKER_ALLOW_MOCK", "true")

    worker = ocr_event_worker.OCRWorker(
        storage=storage,
        event_bus=event_bus,
        input_stream="document.received",
        start_at_latest=False,
    )

    assert worker.run_once() == 1

    completed = event_bus.consume("ocr.completed")
    assert completed[0]["data"]["engine_used"] == "mock"
    assert completed[0]["data"]["document_type"] == "digital_pdf"
    assert b"Banco do Brasil" in storage.get_bytes(completed[0]["data"]["raw_text_uri"])


def test_ocr_worker_sends_invalid_event_to_dlq(tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    event_bus = LocalJsonlEventBus(tmp_path / "events")
    event_bus.publish("document.received", {"event_type": "document.received", "document_id": str(uuid4())})

    worker = ocr_event_worker.OCRWorker(
        storage=storage,
        event_bus=event_bus,
        input_stream="document.received",
        start_at_latest=False,
    )

    assert worker.run_once() == 1
    dlq = event_bus.consume("document.received.dlq")
    assert len(dlq) == 1
    assert dlq[0]["source"] == "backend-ocr"
    assert dlq[0]["stream"] == "document.received"
