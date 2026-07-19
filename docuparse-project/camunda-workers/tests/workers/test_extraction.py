from workers.extraction import _extract_fields


async def test_extract_fields_uses_provided_schema_config_id(mock_core_api):
    mock_core_api.post("/api/ocr/documents/doc-1/langextract").respond(
        200,
        json={
            "status": "EXTRACTION_COMPLETED",
            "extraction_result": {
                "schema_id": "schema-1",
                "schema_version": "1",
                "confidence": 0.98,
                "requires_human_validation": False,
            },
        },
    )

    result = await _extract_fields(document_id="doc-1", tenant_id="default", schema_config_id="schema-1")

    assert result["extraction_skipped"] is False
    assert result["extraction_confidence"] == 0.98


async def test_extract_fields_falls_back_to_shared_schema_resolver_when_no_id_given(
    mock_core_api,
):
    mock_core_api.get("/api/ocr/layout-configs").respond(
        200,
        json=[
            {
                "layout": "boleto_v1",
                "document_type": "boleto",
                "schema_config_id": "schema-2",
                "is_active": True,
            }
        ],
    )
    mock_core_api.post("/api/ocr/documents/doc-1/langextract").respond(
        200,
        json={
            "status": "EXTRACTION_COMPLETED",
            "extraction_result": {
                "schema_id": "schema-2",
                "schema_version": "1",
                "confidence": 0.7,
                "requires_human_validation": True,
            },
        },
    )

    result = await _extract_fields(
        document_id="doc-1", tenant_id="default", layout="boleto_v1", document_type="boleto"
    )

    assert result["extraction_skipped"] is False
    assert result["schema_id"] == "schema-2"


async def test_extract_fields_skips_when_no_schema_resolvable(mock_core_api):
    mock_core_api.get("/api/ocr/layout-configs").respond(200, json=[])

    result = await _extract_fields(
        document_id="doc-1", tenant_id="default", layout="unknown_layout", document_type="x"
    )

    assert result["extraction_skipped"] is True
    assert result["extraction_requires_human_validation"] is True
    # extractionConfidence must always be a defined number for Gateway_0kaeakc's
    # ">" comparison in flow.bpmn — a missing key here would throw a NOT_COMPARABLE
    # incident at runtime instead of routing to the "Não" (human review) branch.
    assert result["extraction_confidence"] == 0.0
