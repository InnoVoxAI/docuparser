from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from api import app as app_module
from api.app import app
from application import extraction_event_worker as worker_module
from application.extraction_event_worker import (
    ExtractionWorker,
    handle_layout_classified_event,
)
from docuparse_events import LocalJsonlEventBus
from docuparse_storage import LocalStorage
from domain import backend_core_client
from domain.schemas import ExtractedDocument
from events import validate_event
from fastapi.testclient import TestClient

BOLETO_TEXT = (
    "Beneficiario: ACME LTDA Vencimento 10/05/2026 Valor R$ 123,45 "
    "Linha digitavel 12345.12345 12345.123456 12345.123456 1 12345678901234"
)
BOLETO_SCHEMA = {
    "schema_id": "boleto_default",
    "version": "v1",
    "fields": [{"name": "valor_boleto", "type": "decimal"}],
}


def _fake_llm(raw_text, schema_definition, **kwargs) -> ExtractedDocument:
    return ExtractedDocument(
        schema_id=schema_definition["schema_id"],
        schema_version=schema_definition["version"],
        fields={"valor_boleto": {"value": "123.45", "confidence": 0.9}},
        confidence=0.9,
        requires_human_validation=False,
    )


@pytest.fixture
def catalog_schema(monkeypatch):
    """Worker resolves the layout to BOLETO_SCHEMA and the LLM is mocked."""
    monkeypatch.setattr(
        worker_module,
        "fetch_schema_for_layout",
        lambda **kwargs: (BOLETO_SCHEMA, 0.75),
    )
    monkeypatch.setattr(worker_module, "extract_with_llm", _fake_llm)


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {
        "status": "healthy",
        "service": "docuparse-langextract-service",
    }
    assert client.get("/ready").json() == {
        "status": "ready",
        "service": "docuparse-langextract-service",
    }


def test_extract_endpoint_uses_schema_definition(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "extract_with_llm", _fake_llm)
    client = TestClient(app)

    response = client.post(
        "/api/v1/extract",
        json={
            "raw_text": BOLETO_TEXT,
            "layout": "boleto_bb",
            "document_type": "scanned_image",
            "schema_definition": BOLETO_SCHEMA,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["schema_id"] == "boleto_default"
    assert data["fields"]["valor_boleto"]["value"] == "123.45"


def test_extract_endpoint_requires_schema_definition() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/extract", json={"raw_text": BOLETO_TEXT})

    assert response.status_code == 422


def _layout_classified_payload(storage, layout: str = "boleto_bb") -> dict:
    tenant_id = "tenant-demo"
    document_id = uuid4()
    raw = storage.put_bytes(
        f"documents/{tenant_id}/{document_id}/ocr/raw_text.json",
        json.dumps({"raw_text": BOLETO_TEXT}).encode("utf-8"),
    )
    return {
        "event_id": str(uuid4()),
        "event_type": "layout.classified",
        "event_version": "v1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "document_id": str(document_id),
        "correlation_id": str(uuid4()),
        "source": "layout-service",
        "data": {
            "layout": layout,
            "confidence": 0.9,
            "document_type": "scanned_image",
            "requires_human_validation": False,
            "metadata": {"raw_text_uri": raw.uri},
        },
    }


def test_layout_classified_becomes_extraction_completed(
    tmp_path, catalog_schema
) -> None:
    storage = LocalStorage(tmp_path / "objects")
    publisher = LocalJsonlEventBus(tmp_path / "events")
    payload = _layout_classified_payload(storage)

    output = handle_layout_classified_event(payload, storage, publisher)

    validated = validate_event(output)
    assert validated.event_type == "extraction.completed"
    assert output["data"]["schema_id"] == "boleto_default"
    assert publisher.consume("extraction.completed") == [output]


def test_layout_without_catalog_schema_publishes_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        worker_module, "fetch_schema_for_layout", lambda **kwargs: (None, 0.75)
    )
    storage = LocalStorage(tmp_path / "objects")
    publisher = LocalJsonlEventBus(tmp_path / "events")

    output = handle_layout_classified_event(
        _layout_classified_payload(storage, layout="generic"), storage, publisher
    )

    assert output is None
    assert publisher.consume("extraction.completed") == []


def test_extraction_worker_consumes_layout_classified_stream(
    tmp_path, catalog_schema
) -> None:
    storage = LocalStorage(tmp_path / "objects")
    event_bus = LocalJsonlEventBus(tmp_path / "events")
    event_bus.publish("layout.classified", _layout_classified_payload(storage))

    worker = ExtractionWorker(
        storage=storage, event_bus=event_bus, start_at_latest=False
    )

    assert worker.run_once() == 1
    outputs = event_bus.consume("extraction.completed")
    assert len(outputs) == 1
    assert outputs[0]["data"]["schema_id"] == "boleto_default"


def test_extraction_worker_sends_invalid_event_to_dlq(tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    event_bus = LocalJsonlEventBus(tmp_path / "events")
    event_bus.publish(
        "layout.classified",
        {"event_type": "layout.classified", "document_id": str(uuid4())},
    )

    worker = ExtractionWorker(
        storage=storage, event_bus=event_bus, start_at_latest=False
    )

    assert worker.run_once() == 1
    dlq = event_bus.consume("layout.classified.dlq")
    assert len(dlq) == 1
    assert dlq[0]["source"] == "langextract-service"
    assert dlq[0]["stream"] == "layout.classified"


def test_schema_lookup_sends_tenant_and_tags_definition(monkeypatch) -> None:
    requests = []

    def fake_get_json(url, headers):
        requests.append((url, headers))
        if url.endswith("/layout-configs"):
            return [
                {
                    "layout": "boleto_generico",
                    "document_type": "",
                    "is_active": True,
                    "schema_config_id": "abc",
                    "confidence_threshold": 0.8,
                }
            ]
        return {
            "schema_id": "boleto_default",
            "version": "v1",
            "definition": {"fields": [{"name": "valor_boleto"}]},
        }

    monkeypatch.setattr(backend_core_client, "_get_json", fake_get_json)

    definition, threshold = backend_core_client.fetch_schema_for_layout(
        tenant_id="demo", layout="boleto_generico", document_type="scanned_image"
    )

    assert all(headers["X-Tenant"] == "demo" for _, headers in requests)
    assert definition["schema_id"] == "boleto_default"
    assert definition["version"] == "v1"
    assert threshold == 0.8
