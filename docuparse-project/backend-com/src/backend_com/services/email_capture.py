from __future__ import annotations

from backend_com.services.document_ingest import DuplicateDocumentError, ingest_document


def process_email_attachments(
    *,
    tenant_id: str,
    attachments: list[dict],
    sender: str | None = None,
    message_id: str | None = None,
    subject: str | None = None,
    provider: str = "manual",
) -> dict:
    documents: list[dict] = []
    duplicate_count = 0
    for index, attachment in enumerate(attachments, start=1):
        metadata = {
            "provider": provider,
            "message_id": message_id,
            "subject": subject,
            "attachment_index": index,
        }
        try:
            documents.append(
                ingest_document(
                    tenant_id=tenant_id,
                    channel="email",
                    filename=attachment["filename"],
                    content_type=attachment["content_type"],
                    content=attachment["content"],
                    sender=sender,
                    metadata=metadata,
                )
            )
        except DuplicateDocumentError:
            duplicate_count += 1
    return {"documents": documents, "duplicate_count": duplicate_count}
