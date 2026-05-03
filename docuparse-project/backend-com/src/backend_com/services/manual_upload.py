from __future__ import annotations

from backend_com.services.document_ingest import ingest_document


def process_manual_upload(
    *,
    tenant_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    sender: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return ingest_document(
        tenant_id=tenant_id,
        channel="manual",
        filename=filename,
        content_type=content_type,
        content=content,
        sender=sender,
        metadata=metadata,
    )
