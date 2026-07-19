from workers.reprocessing import _reset_for_reprocessing


async def test_reset_for_reprocessing_calls_reset_endpoint(mock_core_api):
    mock_core_api.post("/api/ocr/documents/doc-1/reset-for-reprocessing").respond(
        200,
        json={"status": "LAYOUT_CLASSIFIED"},
    )

    result = await _reset_for_reprocessing(document_id="doc-1", tenant_id="default")

    assert result["doc_status"] == "LAYOUT_CLASSIFIED"
