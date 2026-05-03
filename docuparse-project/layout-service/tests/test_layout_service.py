from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from api.app import app
from application.layout_event_worker import LayoutWorker, handle_ocr_completed_event
from docuparse_events import LocalJsonlEventBus
from docuparse_storage import LocalStorage
from domain.classifier import classify_layout
from events import validate_event


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "healthy", "service": "docuparse-layout-service"}
    assert client.get("/ready").json() == {"status": "ready", "service": "docuparse-layout-service"}


def test_classify_layout_endpoint() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/classify-layout",
        json={
            "raw_text": "Banco do Brasil 001 boleto linha digitavel cedente vencimento",
            "document_type": "scanned_image",
        },
    )

    assert response.status_code == 200
    assert response.json()["layout"] == "boleto_bb"
    assert response.json()["confidence"] >= 0.7


def test_initial_layout_heuristics() -> None:
    fixtures = {
        "boleto_caixa": "Caixa Economica Federal 104 boleto linha digitavel cedente vencimento",
        "boleto_bb": "Banco do Brasil 001 boleto linha digitavel cedente vencimento",
        "boleto_bradesco": "Bradesco 237 boleto linha digitavel beneficiario vencimento",
        "fatura_energia": "Energia eletrica kWh unidade consumidora consumo distribuidora vencimento",
        "fatura_condominio": "Condominio unidade rateio assembleia sindico vencimento boleto",
        "generic": "recibo simples sem layout conhecido",
    }

    for expected, raw_text in fixtures.items():
        assert classify_layout(raw_text).layout == expected


def test_ocr_completed_becomes_layout_classified(tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    publisher = LocalJsonlEventBus(tmp_path / "events")
    tenant_id = "tenant-demo"
    document_id = uuid4()
    raw = storage.put_bytes(
        f"documents/{tenant_id}/{document_id}/ocr/raw_text.json",
        json.dumps(
            {
                "raw_text": "Bradesco 237 boleto linha digitavel beneficiario vencimento",
                "document_type": "scanned_image",
            }
        ).encode("utf-8"),
    )
    payload = {
        "event_id": str(uuid4()),
        "event_type": "ocr.completed",
        "event_version": "v1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "document_id": str(document_id),
        "correlation_id": str(uuid4()),
        "source": "backend-ocr",
        "data": {
            "raw_text_uri": raw.uri,
            "raw_text_preview": "Bradesco 237 boleto",
            "document_type": "scanned_image",
            "engine_used": "mock",
            "confidence": None,
            "processing_time_seconds": 0.01,
            "artifacts": {},
            "metadata": {},
        },
    }

    output = handle_ocr_completed_event(payload, storage, publisher)

    validated = validate_event(output)
    assert validated.event_type == "layout.classified"
    assert output["data"]["layout"] == "boleto_bradesco"
    assert publisher.consume("layout.classified") == [output]


def test_layout_worker_consumes_ocr_completed_stream(tmp_path) -> None:
    storage = LocalStorage(tmp_path / "objects")
    event_bus = LocalJsonlEventBus(tmp_path / "events")
    tenant_id = "tenant-demo"
    document_id = uuid4()
    raw = storage.put_bytes(
        f"documents/{tenant_id}/{document_id}/ocr/raw_text.json",
        json.dumps(
            {
                "raw_text": "Banco do Brasil 001 boleto linha digitavel cedente vencimento",
                "document_type": "digital_pdf",
            }
        ).encode("utf-8"),
    )
    event_bus.publish(
        "ocr.completed",
        {
            "event_id": str(uuid4()),
            "event_type": "ocr.completed",
            "event_version": "v1",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "document_id": str(document_id),
            "correlation_id": str(uuid4()),
            "source": "backend-ocr",
            "data": {
                "raw_text_uri": raw.uri,
                "raw_text_preview": "Banco do Brasil 001",
                "document_type": "digital_pdf",
                "engine_used": "docling",
                "confidence": None,
                "processing_time_seconds": 0.01,
                "artifacts": {},
                "metadata": {},
            },
        },
    )

    worker = LayoutWorker(storage=storage, event_bus=event_bus, start_at_latest=False)

    assert worker.run_once() == 1
    outputs = event_bus.consume("layout.classified")
    assert len(outputs) == 1
    assert outputs[0]["data"]["layout"] == "boleto_bb"
