from workers.document import _archive_document, _register_document


def _register_kwargs(**overrides):
    kwargs = {
        "tenant_id": "default",
        "document_id": "doc-1",
        "file_uri": "documents/default/doc-1/original/file.pdf",
        "original_filename": "file.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "abc123",
    }
    kwargs.update(overrides)
    return kwargs


async def test_register_document_returns_file_valid_true(mock_core_api):
    mock_core_api.post("/api/ocr/events/document-received").respond(
        200,
        json={"status": "RECEIVED", "file_valid": True, "rejection_reason": ""},
    )

    result = await _register_document(**_register_kwargs())

    assert result["doc_status"] == "RECEIVED"
    assert result["file_valid"] is True
    assert result["rejection_reason"] == ""
    assert result["duplicate"] is False


async def test_register_document_returns_file_valid_false_with_reason(mock_core_api):
    mock_core_api.post("/api/ocr/events/document-received").respond(
        200,
        json={
            "status": "REJECTED",
            "file_valid": False,
            "rejection_reason": "Arquivo corrompido",
        },
    )

    result = await _register_document(**_register_kwargs())

    assert result["file_valid"] is False
    assert result["rejection_reason"] == "Arquivo corrompido"


async def test_register_document_duplicate_defaults_file_valid_true(mock_core_api):
    mock_core_api.post("/api/ocr/events/document-received").respond(
        409,
        json={"status": "RECEIVED"},
    )

    result = await _register_document(**_register_kwargs())

    assert result["duplicate"] is True
    assert result["file_valid"] is True
    assert result["rejection_reason"] == ""


async def test_archive_document_calls_archive_endpoint(mock_core_api):
    mock_core_api.post("/api/ocr/documents/doc-1/archive").respond(
        200,
        json={"status": "ARCHIVED"},
    )

    result = await _archive_document(document_id="doc-1", tenant_id="default")

    assert result["doc_status"] == "ARCHIVED"


async def test_register_document_sends_x_tenant_header(mock_core_api):
    route = mock_core_api.post("/api/ocr/events/document-received").respond(
        200,
        json={"status": "RECEIVED", "file_valid": True, "rejection_reason": ""},
    )

    await _register_document(**_register_kwargs(tenant_id="tenant-demo"))

    assert route.calls.last.request.headers["X-Tenant"] == "tenant-demo"
