from workers.observability import _log_failure


async def test_log_failure_returns_logged_at_timestamp():
    result = await _log_failure(
        document_id="doc-1",
        tenant_id="default",
        failure_reason="invalid_file",
        ocr_retry_count=0,
    )

    assert "logged_at" in result
    assert result["logged_at"]


async def test_log_failure_defaults_retry_count_to_zero():
    result = await _log_failure(
        document_id="doc-1",
        tenant_id="default",
        failure_reason="invalid_file",
    )

    assert "logged_at" in result


async def test_log_failure_payload_shape_consistent_across_call_sites():
    """docuparse-log-failure is reused by both Activity_10ryy35 (invalid file,
    US1) and Activity_07jkc9p (unreadable after retries, US2) in flow.bpmn.
    Both call sites must produce the same result shape."""
    invalid_file_result = await _log_failure(
        document_id="doc-1",
        tenant_id="default",
        failure_reason="Arquivo corrompido",
        ocr_retry_count=0,
        failure_step="Task_Ingestion",
    )
    unreadable_result = await _log_failure(
        document_id="doc-2",
        tenant_id="default",
        failure_reason="Documento ilegível após 3 tentativas de processamento",
        ocr_retry_count=3,
        failure_step="Task_OCR",
    )

    assert set(invalid_file_result.keys()) == set(unreadable_result.keys()) == {"logged_at"}
