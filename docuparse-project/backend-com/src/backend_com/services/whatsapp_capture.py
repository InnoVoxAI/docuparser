from __future__ import annotations

import base64

from backend_com.services.document_ingest import ingest_document


def process_whatsapp_media(
    *,
    tenant_id: str,
    media_items: list[dict],
    sender: str | None = None,
    message_sid: str | None = None,
    body: str | None = None,
) -> list[dict]:
    results: list[dict] = []
    for index, media in enumerate(media_items, start=1):
        content = media.get("content")
        if content is None and media.get("content_base64"):
            content = base64.b64decode(media["content_base64"])
        if content is None:
            raise ValueError("media content is required when MediaUrl download is unavailable")

        metadata = {
            "provider": "twilio",
            "message_sid": message_sid,
            "body": body,
            "media_index": index,
            "media_url": media.get("media_url"),
        }
        results.append(
            ingest_document(
                tenant_id=tenant_id,
                channel="whatsapp",
                filename=media.get("filename") or f"whatsapp-media-{index}",
                content_type=media["content_type"],
                content=content,
                sender=sender,
                metadata=metadata,
            )
        )
    return results
