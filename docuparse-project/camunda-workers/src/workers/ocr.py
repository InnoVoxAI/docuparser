"""Workers for OCR processing via backend-core."""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client

log = structlog.get_logger()

process_ocr = ZeebeTaskRouter()
reprocess_ocr = ZeebeTaskRouter()


@process_ocr.task(
    task_type="docuparse-process-ocr",
    timeout_ms=200_000,
    max_jobs_to_activate=3,
)
async def _process_ocr(document_id: str, **kwargs) -> dict:
    """Run OCR on a document. Returns updated document state."""
    log.info("ocr_starting", document_id=document_id)

    async with core_client(timeout=195.0) as client:
        resp = await client.post(f"/api/ocr/documents/{document_id}/process-ocr")
        resp.raise_for_status()
        data = resp.json()

    log.info("ocr_done", document_id=document_id, status=data.get("status"))
    return {
        "doc_status": data.get("status"),
        "document_type": data.get("document_type"),
        "raw_text_uri": data.get("raw_text_uri"),
        "ocr_engine": data.get("metadata", {}).get("ocr", {}).get("engine_used"),
    }


@reprocess_ocr.task(
    task_type="docuparse-reprocess-ocr",
    timeout_ms=200_000,
    max_jobs_to_activate=3,
)
async def _reprocess_ocr(document_id: str, **kwargs) -> dict:
    """Re-run OCR on a document (e.g. after rejection)."""
    log.info("ocr_reprocess_starting", document_id=document_id)

    async with core_client(timeout=195.0) as client:
        resp = await client.post(f"/api/ocr/documents/{document_id}/reprocess-ocr")
        resp.raise_for_status()
        data = resp.json()

    log.info("ocr_reprocess_done", document_id=document_id, status=data.get("status"))
    return {
        "doc_status": data.get("status"),
        "document_type": data.get("document_type"),
        "raw_text_uri": data.get("raw_text_uri"),
        "ocr_engine": data.get("metadata", {}).get("ocr", {}).get("engine_used"),
    }
