"""Workers for document registration and retrieval in backend-core."""
from datetime import datetime, timezone

import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client

log = structlog.get_logger()

register_document = ZeebeTaskRouter()
get_document = ZeebeTaskRouter()
delete_document = ZeebeTaskRouter()


@register_document.task(
    task_type="docuparse-register-document",
    timeout_ms=15_000,
    max_jobs_to_activate=10,
)
async def _register_document(
    tenant_id: str,
    document_id: str,
    file_uri: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
    channel: str = "manual",
    correlation_id: str = "",
    sender: str = "",
    **kwargs,
) -> dict:
    """Register a received document in backend-core (idempotent)."""
    payload = {
        "event_id": document_id,
        "event_type": "document.received",
        "event_version": "v1",
        "tenant_id": tenant_id,
        "document_id": document_id,
        "correlation_id": correlation_id or document_id,
        "source": "camunda-workers",
        "data": {
            "channel": channel,
            "sender": sender,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "file": {
                "uri": file_uri,
                "filename": original_filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "sha256": sha256,
            },
        },
    }

    async with core_client(timeout=12.0) as client:
        resp = await client.post("/api/ocr/events/document-received", json=payload)
        log.info(
            "register_document_response",
            document_id=document_id,
            status=resp.status_code,
            body=resp.text[:500],
        )
        if resp.status_code == 409:
            log.info("document_already_registered", document_id=document_id)
            data = resp.json()
            return {"duplicate": True, "doc_status": data.get("status", "RECEIVED")}
        resp.raise_for_status()
        data = resp.json()

    log.info("document_registered", document_id=document_id, status=data.get("status"))
    return {"duplicate": False, "doc_status": data.get("status", "RECEIVED")}


@get_document.task(
    task_type="docuparse-get-document",
    timeout_ms=10_000,
    max_jobs_to_activate=10,
)
async def _get_document(document_id: str, **kwargs) -> dict:
    """Fetch current document state from backend-core."""
    async with core_client(timeout=8.0) as client:
        resp = await client.get(f"/api/ocr/documents/{document_id}")
        resp.raise_for_status()
        data = resp.json()

    log.info("document_fetched", document_id=document_id, status=data.get("status"))
    return {
        "doc_status": data.get("status"),
        "document_type": data.get("document_type"),
        "layout": data.get("layout"),
        "raw_text_uri": data.get("raw_text_uri"),
    }


@delete_document.task(
    task_type="docuparse-delete-document",
    timeout_ms=10_000,
    max_jobs_to_activate=5,
)
async def _delete_document(document_id: str, **kwargs) -> dict:
    """Delete a document from backend-core."""
    async with core_client(timeout=8.0) as client:
        resp = await client.delete(f"/api/ocr/documents/{document_id}/delete")
        resp.raise_for_status()

    log.info("document_deleted", document_id=document_id)
    return {"deleted": True}
