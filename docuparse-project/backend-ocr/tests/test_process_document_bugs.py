from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app
from api.routes import document as document_route
from application import process_document as process_module
from infrastructure.engines import openrouter_engine


class FakeEngine:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or {"raw_text": "fallback text", "_meta": {"text_length": 13}}
        self.error = error

    def process(self, file_bytes, metadata):
        if self.error:
            raise self.error
        return self.result


class FakeExtractor:
    def extract(self, ocr_result):
        return {
            "fields": {"amount": "10,00"},
            "final_score": 0.8,
            "field_confidence": {},
            "low_confidence_fields": [],
            "_meta": {},
        }


class FailingExtractor:
    def __init__(self):
        raise AssertionError("FieldExtractor should not run in the main OCR path")


def test_process_document_calls_classifier_with_filename_and_content(monkeypatch) -> None:
    calls = []

    def fake_classify(filename, content):
        calls.append((filename, content))
        return "scanned_image"

    monkeypatch.setattr(process_module, "classify_document", fake_classify)
    monkeypatch.setattr(process_module.engine_resolver, "get_engine", lambda doc_type, selected=None: "fake")
    monkeypatch.setattr(process_module, "ENGINE_REGISTRY", {"fake": FakeEngine()})
    monkeypatch.setattr(process_module, "FieldExtractor", FakeExtractor)

    result = process_module.process_document(b"abc", "scan.png")

    assert calls == [("scan.png", b"abc")]
    assert result["raw_text"] == "fallback text"
    assert result["fields"] == {}
    assert result["semantic_extraction_enabled"] is False


def test_process_document_skips_semantic_extraction_by_default(monkeypatch) -> None:
    monkeypatch.setattr(process_module, "classify_document", lambda filename, content: "scanned_image")
    monkeypatch.setattr(process_module.engine_resolver, "get_engine", lambda doc_type, selected=None: "fake")
    monkeypatch.setattr(process_module, "ENGINE_REGISTRY", {"fake": FakeEngine()})
    monkeypatch.setattr(process_module, "FieldExtractor", FailingExtractor)

    result = process_module.process_document(b"abc", "scan.png")

    assert result["fields"] == {}
    assert result["final_score"] == 0.0
    assert result["debug"]["field_extraction_meta"]["semantic_extraction"] == "disabled"


def test_process_document_runs_legacy_extraction_when_requested(monkeypatch) -> None:
    monkeypatch.setattr(process_module, "classify_document", lambda filename, content: "scanned_image")
    monkeypatch.setattr(process_module.engine_resolver, "get_engine", lambda doc_type, selected=None: "fake")
    monkeypatch.setattr(process_module, "ENGINE_REGISTRY", {"fake": FakeEngine()})
    monkeypatch.setattr(process_module, "FieldExtractor", FakeExtractor)

    result = process_module.process_document(b"abc", "scan.png", legacy_extraction=True)

    assert result["fields"] == {"amount": "10,00"}
    assert result["final_score"] == 0.8
    assert result["semantic_extraction_enabled"] is True


def test_process_document_routes_digital_pdf_to_docling(monkeypatch) -> None:
    monkeypatch.setattr(process_module, "classify_document", lambda filename, content: "digital_pdf")
    monkeypatch.setattr(
        process_module,
        "ENGINE_REGISTRY",
        {
            "docling": FakeEngine({"raw_text": "texto pdf", "_meta": {"engine": "docling"}}),
            "openrouter": FakeEngine({"raw_text": "wrong", "_meta": {"engine": "openrouter"}}),
        },
    )
    monkeypatch.setattr(process_module, "FieldExtractor", FakeExtractor)

    result = process_module.process_document(b"%PDF", "texto.pdf")

    assert result["engine_used"] == "docling"
    assert result["raw_text"] == "texto pdf"


def test_process_document_routes_image_pdf_to_openrouter(monkeypatch) -> None:
    monkeypatch.setattr(process_module, "classify_document", lambda filename, content: "scanned_image")
    monkeypatch.setattr(
        process_module,
        "ENGINE_REGISTRY",
        {
            "docling": FakeEngine({"raw_text": "wrong", "_meta": {"engine": "docling"}}),
            "openrouter": FakeEngine({"raw_text": "texto imagem", "_meta": {"engine": "openrouter"}}),
        },
    )
    monkeypatch.setattr(process_module, "FieldExtractor", FakeExtractor)

    result = process_module.process_document(b"%PDF", "scan.pdf")

    assert result["engine_used"] == "openrouter"
    assert result["preprocessing_hint"] == "render_pdf_or_image_for_vision_ocr"
    assert result["classification_engine_preprocessing_hints"]["openrouter"] == "render_pdf_or_image_for_vision_ocr"
    assert result["raw_text"] == "texto imagem"


def test_process_document_fallback_does_not_use_undefined_ocr_result(monkeypatch) -> None:
    monkeypatch.setattr(process_module, "classify_document", lambda filename, content: "scanned_image")
    monkeypatch.setattr(process_module.engine_resolver, "get_engine", lambda doc_type, selected=None: "primary")
    monkeypatch.setattr(
        process_module,
        "ENGINE_REGISTRY",
        {
            "primary": FakeEngine(error=RuntimeError("primary failed")),
            "tesseract": FakeEngine({"raw_text": "fallback text with enough tokens", "_meta": {"text_length": 32}}),
        },
    )
    monkeypatch.setattr(process_module, "FieldExtractor", FakeExtractor)

    result = process_module.process_document(b"abc", "scan.png")

    assert result["engine_used"] == "primary_with_tesseract_fallback"
    assert result["debug"]["engine_meta"]["fallback_triggered"] is True


def test_process_endpoint_preserves_empty_file_400() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/process",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo vazio"


def test_process_endpoint_accepts_fixture_file(monkeypatch) -> None:
    def fake_process_document(file_bytes, filename, selected_engine=None, timeout_s=120, legacy_extraction=False):
        return {
            "fields": {},
            "field_positions": {},
            "final_score": 0.0,
            "field_confidence": {},
            "low_confidence_fields": [],
            "raw_text": "fixture text",
            "raw_text_fallback": "",
            "document_type": "scanned_image",
            "engine_used": "mock",
            "processing_time_seconds": 0.01,
            "filename": filename,
            "semantic_extraction_enabled": False,
            "document_info": {},
            "entities": {},
            "tables": [],
            "totals": {},
            "debug": {},
        }

    monkeypatch.setattr(document_route, "process_document", fake_process_document)
    client = TestClient(app)

    response = client.post(
        "/api/v1/process",
        files={"file": ("fixture.png", b"not-empty", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["raw_text"] == "fixture text"


def test_readiness_fails_without_openrouter_config(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["missing"] == ["OPENROUTER_API_KEY", "OPENROUTER_MODEL"]


def test_engines_include_runtime_status() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/engines")

    assert response.status_code == 200
    assert all("status" in engine for engine in response.json()["engines"])


def test_openrouter_image_uses_key_values_when_extracted_text_is_empty(monkeypatch) -> None:
    def fake_call_openrouter(image_bgr, page_label="image_1", timeout_s=120):
        return {
            "page": page_label,
            "with_handwritten_text": True,
            "extracted_text": "",
            "language": "pt",
            "confidence_0_1": 0.9,
            "key_values": [
                {"key": "Valor", "value": "120,00"},
                {"key": "Recebi(emos) de", "value": "RECIFE COLONIAL"},
                {"key": "Correspondente a", "value": "DIARIA PORTEIRO DIURNO"},
            ],
        }

    monkeypatch.setattr(openrouter_engine, "_call_openrouter", fake_call_openrouter)

    fixture = Path(__file__).resolve().parents[3] / "docs_teste" / "PHOTO-2026-01-08-18-44-00.jpg"
    result = openrouter_engine.OpenRouterOCREngine().process(fixture.read_bytes(), {"filename": fixture.name})

    assert result["raw_text"] == (
        "Valor: 120,00\n"
        "Recebi(emos) de: RECIFE COLONIAL\n"
        "Correspondente a: DIARIA PORTEIRO DIURNO"
    )


def test_openrouter_image_retries_with_qwen_when_text_is_empty(monkeypatch) -> None:
    calls = []

    def fake_call_openrouter(image_bgr, page_label="image_1", timeout_s=120, model_override=None):
        calls.append((page_label, model_override))
        if model_override == "qwen/qwen2.5-vl-72b-instruct":
            return {
                "page": page_label,
                "with_handwritten_text": False,
                "extracted_text": "texto recuperado pelo qwen",
                "language": "pt",
                "confidence_0_1": 0.82,
                "key_values": [],
            }
        return {
            "page": page_label,
            "with_handwritten_text": False,
            "extracted_text": "",
            "language": "pt",
            "confidence_0_1": 0,
            "key_values": [],
        }

    monkeypatch.setenv("OPENROUTER_MODEL", "primary/model")
    monkeypatch.delenv("OPENROUTER_FALLBACK_MODEL", raising=False)
    monkeypatch.setattr(openrouter_engine, "_call_openrouter", fake_call_openrouter)

    fixture = Path(__file__).resolve().parents[3] / "docs_teste" / "PHOTO-2026-01-08-18-44-00.jpg"
    result = openrouter_engine.OpenRouterOCREngine().process(fixture.read_bytes(), {"filename": fixture.name})

    assert calls == [
        ("image_1", None),
        ("image_1_retry", "qwen/qwen2.5-vl-72b-instruct"),
    ]
    assert result["raw_text"] == "texto recuperado pelo qwen"
    assert result["_meta"]["empty_text_retry"] is True
    assert result["_meta"]["fallback_model"] == "qwen/qwen2.5-vl-72b-instruct"
