from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from pyzeebe import ZeebeClient, create_insecure_channel

from backend_com.config import settings

logger = logging.getLogger(__name__)

# ingest_document() (the only caller) is synchronous but always runs inside
# uvicorn's already-running event loop, so asyncio.run() can't be called
# inline there. Publish on a dedicated thread with its own fresh loop instead
# — blocking is fine since ingest_document already blocks on the equivalent
# core-sync HTTP call.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="camunda-trigger")

# Reuses the whatsapp entry point (feature 014's docuparse-pipeline only has
# message start events for email/whatsapp; manual uploads piggyback on the
# whatsapp one rather than adding a third BPMN entry point). The `channel`
# variable sent below still reflects the document's real channel — this only
# controls which BPMN start event fires, not what gets recorded on Document.
MESSAGE_NAME = "docuparse-file-received-whatsapp"

_PUBLISH_TIMEOUT_SECONDS = 5.0


def start_docuparse_pipeline(
    *,
    tenant_id: str,
    document_id: str,
    file_uri: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
    channel: str,
    correlation_id: str,
) -> str:
    """Publish the docuparse-pipeline start message for a just-ingested document.

    Synchronous (see module docstring above on why) and never raises — mirrors
    the non-fatal pattern in `document_ingest.py::_sync_document_received_to_core`
    so an upload still succeeds even when Zeebe / the `camunda` compose profile
    isn't running. Returns "published" or "failed".
    """
    variables = {
        "documentId": document_id,
        "tenantId": tenant_id,
        "fileUri": file_uri,
        "originalFilename": original_filename,
        "contentType": content_type,
        "sizeBytes": size_bytes,
        "sha256": sha256,
        "channel": channel,
        "correlationId": correlation_id,
    }
    try:
        _executor.submit(_publish_in_new_loop, variables).result(timeout=_PUBLISH_TIMEOUT_SECONDS)
        return "published"
    except Exception as exc:
        logger.warning("camunda_pipeline_trigger_failed", extra={"error": str(exc)})
        return "failed"


def _publish_in_new_loop(variables: dict) -> None:
    asyncio.run(asyncio.wait_for(_publish(variables), timeout=_PUBLISH_TIMEOUT_SECONDS))


async def _publish(variables: dict) -> None:
    channel = create_insecure_channel(grpc_address=settings.zeebe_address)
    try:
        client = ZeebeClient(channel)
        await client.publish_message(
            name=MESSAGE_NAME,
            correlation_key="",
            variables=variables,
        )
    finally:
        await channel.close()
