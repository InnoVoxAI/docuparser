"""Worker to reset a rejected document for a fresh extraction attempt."""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client

log = structlog.get_logger()

reset_for_reprocessing = ZeebeTaskRouter()


@reset_for_reprocessing.task(
    task_type="docuparse-reset-for-reprocessing",
    timeout_ms=15_000,
    max_jobs_to_activate=5,
)
async def _reset_for_reprocessing(document_id: str, tenant_id: str, **kwargs) -> dict:
    """Clear the prior extraction result and return the document to a
    re-extractable state (operator chose "reprocess" after rejecting it)."""
    async with core_client(tenant_id, timeout=12.0) as client:
        resp = await client.post(f"/api/ocr/documents/{document_id}/reset-for-reprocessing")
        resp.raise_for_status()
        data = resp.json()

    log.info("document_reset_for_reprocessing", document_id=document_id, status=data.get("status"))
    return {"doc_status": data.get("status")}
