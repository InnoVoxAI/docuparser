"""Worker for structured field extraction via backend-core → langextract-service."""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client

log = structlog.get_logger()

extract_fields = ZeebeTaskRouter()


@extract_fields.task(
    task_type="docuparse-extract-fields",
    timeout_ms=150_000,
    max_jobs_to_activate=3,
)
async def _extract_fields(
    document_id: str,
    layout: str = "",
    document_type: str = "unknown",
    schema_config_id: str = "",
    **kwargs,
) -> dict:
    log.info("extraction_starting", document_id=document_id, layout=layout)

    if not schema_config_id:
        schema_config_id = await _resolve_schema_config_id(layout, document_type)

    if not schema_config_id:
        log.info("extraction_skipped_no_schema", document_id=document_id, layout=layout)
        return {
            "doc_status": "OCR_COMPLETED",
            "extraction_skipped": True,
            "extraction_requires_human_validation": True,
        }

    async with core_client(timeout=145.0) as client:
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
        "extraction_confidence": extraction.get("confidence"),
        "extraction_requires_human_validation": extraction.get("requires_human_validation", True),
    }


async def _resolve_schema_config_id(layout: str, document_type: str) -> str:
    """Look up the active schema config for this layout/document_type combination."""
    if not layout:
        return ""
    try:
        async with core_client(timeout=10.0) as client:
            resp = await client.get("/api/ocr/layout-configs")
            resp.raise_for_status()
            configs = resp.json()

        match = next(
            (c for c in configs if c.get("layout") == layout
             and c.get("document_type") == document_type and c.get("is_active")),
            None,
        ) or next(
            (c for c in configs if c.get("layout") == layout and c.get("is_active")),
            None,
        )
        return match.get("schema_config_id", "") if match else ""
    except Exception as exc:
        log.warning("schema_config_lookup_failed", layout=layout, error=str(exc))
        return ""
