"""Worker for structured field extraction via backend-core → langextract-service."""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client
from workers._schema import resolve_schema_config_id

log = structlog.get_logger()

extract_fields = ZeebeTaskRouter()


@extract_fields.task(
    task_type="docuparse-extract-fields",
    timeout_ms=150_000,
    max_jobs_to_activate=3,
)
async def _extract_fields(
    document_id: str,
    tenant_id: str,
    layout: str = "",
    document_type: str = "unknown",
    schema_config_id: str = "",
    **kwargs,
) -> dict:
    log.info("extraction_starting", document_id=document_id, layout=layout)

    if not schema_config_id:
        schema_config_id = await resolve_schema_config_id(layout, document_type, tenant_id)

    if not schema_config_id:
        log.info("extraction_skipped_no_schema", document_id=document_id, layout=layout)
        return {
            "doc_status": "OCR_COMPLETED",
            "extraction_skipped": True,
            "schema_id": "",
            "schema_version": "",
            "extraction_confidence": 0.0,
            "extraction_requires_human_validation": True,
        }

    async with core_client(tenant_id, timeout=145.0) as client:
        resp = await client.post(
            f"/api/ocr/documents/{document_id}/langextract",
            json={"schema_config_id": schema_config_id},
        )
        resp.raise_for_status()
        data = resp.json()

    extraction = data.get("extraction_result") or {}
    log.info(
        "extraction_done",
        document_id=document_id,
        schema_id=extraction.get("schema_id"),
        confidence=extraction.get("confidence"),
    )
    return {
        "doc_status": data.get("status"),
        "extraction_skipped": False,
        "schema_id": extraction.get("schema_id"),
        "schema_version": extraction.get("schema_version"),
        "extraction_confidence": extraction.get("confidence") or 0.0,
        "extraction_requires_human_validation": extraction.get("requires_human_validation", True),
    }
