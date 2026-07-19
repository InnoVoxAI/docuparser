from workers.layout import _classify_layout


async def test_classify_layout_returns_document_configured_true(mock_layout_api, mock_core_api):
    mock_layout_api.post("/api/v1/classify-layout").respond(
        200,
        json={"layout": "boleto_v1", "confidence": 0.9, "requires_human_validation": False},
    )
    mock_core_api.get("/api/ocr/layout-configs").respond(
        200,
        json=[
            {
                "layout": "boleto_v1",
                "document_type": "boleto",
                "schema_config_id": "schema-1",
                "is_active": True,
            }
        ],
    )

    result = await _classify_layout(document_id="doc-1", tenant_id="default", document_type="boleto")

    assert result["layout"] == "boleto_v1"
    assert result["document_configured"] is True


async def test_classify_layout_returns_document_configured_false_when_no_match(
    mock_layout_api, mock_core_api
):
    mock_layout_api.post("/api/v1/classify-layout").respond(
        200,
        json={"layout": "unknown_layout", "confidence": 0.4, "requires_human_validation": True},
    )
    mock_core_api.get("/api/ocr/layout-configs").respond(200, json=[])

    result = await _classify_layout(document_id="doc-1", tenant_id="default", document_type="boleto")

    assert result["document_configured"] is False
