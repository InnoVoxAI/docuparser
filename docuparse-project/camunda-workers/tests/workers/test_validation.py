import json

from workers.validation import _validate_document


async def test_validate_document_auto_approval(mock_core_api):
    route = mock_core_api.post("/api/ocr/documents/doc-1/validate").respond(
        200,
        json={"status": "APPROVED"},
    )

    result = await _validate_document(
        document_id="doc-1",
        tenant_id="tenant-demo",
        decision="approved",
        notes="auto-approved: confidence>95%",
    )

    assert result["doc_status"] == "APPROVED"
    assert result["validation_decision"] == "approved"
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["decision"] == "approved"
    assert sent_body["notes"] == "auto-approved: confidence>95%"
    assert route.calls.last.request.headers["X-Tenant"] == "tenant-demo"


async def test_validate_document_rejection_requires_notes(mock_core_api):
    route = mock_core_api.post("/api/ocr/documents/doc-1/validate").respond(
        200,
        json={"status": "REJECTED"},
    )

    result = await _validate_document(
        document_id="doc-1",
        tenant_id="default",
        decision="rejected",
        notes="Valor do boleto ilegível",
    )

    assert result["doc_status"] == "REJECTED"
    assert result["validation_decision"] == "rejected"
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["decision"] == "rejected"
    assert sent_body["notes"] == "Valor do boleto ilegível"
