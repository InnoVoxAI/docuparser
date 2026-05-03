from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from api.app import app
from application.extraction_event_worker import handle_layout_classified_event
from docuparse_events import LocalJsonlEventBus
from docuparse_storage import LocalStorage
from domain.extractor import extract_fields
from events import validate_event


BOLETO_TEXT = (
    "Beneficiario: ACME LTDA Vencimento 10/05/2026 Valor R$ 123,45 "
    "Linha digitavel 12345.12345 12345.123456 12345.123456 1 12345678901234"
)


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "healthy", "service": "docuparse-langextract-service"}
    assert client.get("/ready").json() == {"status": "ready", "service": "docuparse-langextract-service"}


def test_extract_endpoint_for_boleto() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/extract",
        json={
            "raw_text": BOLETO_TEXT,
            "layout": "boleto_bb",
            "document_type": "scanned_image",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["schema_id"] == "boleto"
    assert data["schema_version"] == "v1"
    assert data["fields"]["valor"] == "R$ 123,45"
    assert data["confidence"] >= 0.75


def test_versioned_extractors_for_initial_schemas() -> None:
    boleto = extract_fields(BOLETO_TEXT, "boleto_caixa")
    fatura = extract_fields("Unidade 42 consumo 150 kWh vencimento 11/05/2026 total R$ 222,10", "fatura_energia")

    assert boleto.schema_id == "boleto"
    assert boleto.schema_version == "v1"
    assert fatura.schema_id == "fatura"
    assert fatura.schema_version == "v1"


def test_layout_classified_becomes_extraction_completed(tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    publisher = LocalJsonlEventBus(tmp_path / "events")
    tenant_id = "tenant-demo"
    document_id = uuid4()
    raw = storage.put_bytes(
        f"documents/{tenant_id}/{document_id}/ocr/raw_text.json",
        json.dumps({"raw_text": BOLETO_TEXT}).encode("utf-8"),
    )
    payload = {
        "event_id": str(uuid4()),
        "event_type": "layout.classified",
        "event_version": "v1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "document_id": str(document_id),
        "correlation_id": str(uuid4()),
        "source": "layout-service",
        "data": {
            "layout": "boleto_bb",
            "confidence": 0.9,
            "document_type": "scanned_image",
            "requires_human_validation": False,
            "metadata": {
                "raw_text_uri": raw.uri,
            },
        },
    }

    output = handle_layout_classified_event(payload, storage, publisher)

    validated = validate_event(output)
    assert validated.event_type == "extraction.completed"
    assert output["data"]["schema_id"] == "boleto"
    assert publisher.consume("extraction.completed") == [output]
