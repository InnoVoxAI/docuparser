from __future__ import annotations

from services.document_ingest import DuplicateDocumentError, ingest_document


def email_thread_id(message_id: str | None) -> str:
    """Anexos do mesmo e-mail compartilham o Message-ID."""
    message_id = (message_id or "").strip()
    return f"email:{message_id}" if message_id else ""


def process_email_attachments(
    *,
    tenant_id: str,
    attachments: list[dict],
    sender: str | None = None,
    message_id: str | None = None,
    subject: str | None = None,
    provider: str = "manual",
    metadata_channel: dict | None = None,
) -> dict:
    documents: list[dict] = []
    duplicate_count = 0
    for index, attachment in enumerate(attachments, start=1):
        metadata: dict = {
            "provider": provider,
            "message_id": message_id,
            "subject": subject,
            "attachment_index": index,
        }
        if metadata_channel:
            metadata["metadata_channel"] = metadata_channel
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
                    source_thread_id=email_thread_id(message_id),
                )
            )
        except DuplicateDocumentError:
            duplicate_count += 1
    return {"documents": documents, "duplicate_count": duplicate_count}
