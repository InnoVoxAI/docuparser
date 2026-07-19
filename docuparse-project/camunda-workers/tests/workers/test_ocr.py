from workers.ocr import _process_ocr, _reprocess_ocr


async def test_process_ocr_returns_ocr_readable_true(mock_core_api):
    mock_core_api.post("/api/ocr/documents/doc-1/process-ocr").respond(
        200,
        json={
            "status": "OCR_COMPLETED",
            "document_type": "boleto",
            "raw_text_uri": "uri://doc-1",
            "ocr_readable": True,
            "metadata": {"ocr": {"engine_used": "tesseract"}},
        },
    )

    result = await _process_ocr(document_id="doc-1", tenant_id="default")

    assert result["ocr_readable"] is True
    assert result["ocr_engine"] == "tesseract"


async def test_process_ocr_returns_ocr_readable_false(mock_core_api):
    mock_core_api.post("/api/ocr/documents/doc-1/process-ocr").respond(
        200,
        json={
            "status": "OCR_COMPLETED",
            "document_type": "unknown",
            "raw_text_uri": "uri://doc-1",
            "ocr_readable": False,
            "metadata": {"ocr": {"engine_used": "tesseract"}},
        },
    )

    result = await _process_ocr(document_id="doc-1", tenant_id="default")

    assert result["ocr_readable"] is False


async def test_reprocess_ocr_returns_ocr_readable(mock_core_api):
    mock_core_api.post("/api/ocr/documents/doc-1/reprocess-ocr").respond(
        200,
        json={
            "status": "OCR_COMPLETED",
            "document_type": "boleto",
            "raw_text_uri": "uri://doc-1",
            "ocr_readable": True,
            "metadata": {"ocr": {"engine_used": "easyocr"}},
        },
    )

    result = await _reprocess_ocr(document_id="doc-1", tenant_id="default")

    assert result["ocr_readable"] is True
