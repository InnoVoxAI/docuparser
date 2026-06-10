from __future__ import annotations

from pathlib import Path

from domain.classifier import CLASS_DIGITAL_PDF, classify_document


def test_text_pdf_with_more_text_blocks_than_image_blocks_is_digital_pdf() -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "docs_teste"
        / "26116062208629869000101000000000000625120022507574 - Condominio do Edificio Recife Colonial.pdf"
    )

    assert classify_document(fixture.name, fixture.read_bytes()) == CLASS_DIGITAL_PDF
