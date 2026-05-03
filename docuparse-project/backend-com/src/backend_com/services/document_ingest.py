from __future__ import annotations

import logging
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

from docuparse_events import event_bus_from_env
from docuparse_observability import log_event
from docuparse_storage import LocalStorage, document_original_key
from events import DocumentReceivedEvent

from backend_com.config import settings

logger = logging.getLogger(__name__)


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}


def ingest_document(
    *,
    tenant_id: str,
    channel: str,
    filename: str,
    content_type: str,
    content: bytes,
    sender: str | None = None,
    metadata: dict | None = None,
) -> dict:
    if not tenant_id.strip():
        raise ValueError("tenant_id is required")
    if channel not in {"manual", "email", "whatsapp"}:
        raise ValueError(f"unsupported channel: {channel}")
    if not filename.strip():
        raise ValueError("filename is required")
    if not content:
        raise ValueError("file is empty")
    if len(content) > settings.max_upload_bytes:
        raise ValueError("file exceeds max upload size")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"unsupported content_type: {content_type}")

    document_id = uuid4()
    storage = LocalStorage(settings.local_storage_dir)
    stored = storage.put_bytes(document_original_key(tenant_id, str(document_id)), content)

    event = DocumentReceivedEvent(
        tenant_id=tenant_id,
        document_id=document_id,
        correlation_id=uuid4(),
        source="backend-com",
        data={
            "channel": channel,
            "received_at": datetime.now(timezone.utc),
            "sender": sender,
            "file": {
                "uri": stored.uri,
                "content_type": content_type,
                "filename": filename,
                "size_bytes": stored.size_bytes,
                "sha256": stored.sha256,
            },
            "metadata": metadata or {},
        },
    )
    event_payload = event.model_dump(mode="json")
    event_bus_from_env(settings.local_event_dir).publish("document.received", event_payload)
    core_sync_status = _sync_document_received_to_core(event_payload)
    log_event(
        logger,
        "document.received published",
        tenant_id=tenant_id,
        document_id=str(document_id),
        correlation_id=str(event.correlation_id),
        event_type=event.event_type,
        channel=channel,
        file_uri=stored.uri,
        core_sync_status=core_sync_status,
    )

    return {
        "document_id": str(document_id),
        "event_id": str(event.event_id),
        "file_uri": stored.uri,
        "size_bytes": stored.size_bytes,
        "sha256": stored.sha256,
        "event_type": event.event_type,
        "channel": channel,
        "core_sync_status": core_sync_status,
    }


def _sync_document_received_to_core(event_payload: dict) -> str:
    if not settings.backend_core_document_received_url:
        return "disabled"

    body = json.dumps(event_payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.internal_service_token:
        headers["Authorization"] = f"Bearer {settings.internal_service_token}"
    request = urllib.request.Request(
        settings.backend_core_document_received_url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return f"synced:{response.status}"
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        logger.warning("document_received_core_sync_failed", extra={"error": str(exc)})
        return "failed"
