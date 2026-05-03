from __future__ import annotations

from pathlib import Path

from application.process_document import process_document


REAL_PDF = Path(__file__).resolve().parents[3] / "docs_teste" / "AnyScanner_12_09_2025.pdf"


def test_anyscanner_pdf_runs_with_local_tesseract() -> None:
    result = process_document(
        REAL_PDF.read_bytes(),
        REAL_PDF.name,
        selected_engine="tesseract",
        legacy_extraction=False,
    )

    assert result["engine_used"] == "tesseract"
    assert result["document_info"]["page_count"] == 1
    assert len(result["raw_text"].strip()) > 20
    assert result["fields"] == {}
    assert result["semantic_extraction_enabled"] is False
