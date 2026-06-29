"""Worker for ERP export / integration via backend-core.

Approves the document (persisting the validation decision) and triggers
the ERP export if integration settings have it enabled for the tenant.
"""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client

log = structlog.get_logger()

export_erp = ZeebeTaskRouter()


@export_erp.task(
    task_type="docuparse-export-erp",
    timeout_ms=90_000,
    max_jobs_to_activate=5,
)
async def _export_erp(
    document_id: str,
    tenant_id: str = "",
    validation_decision: str = "approved",
    validation_notes: str = "",
    extraction_skipped: bool = False,
    **kwargs,
) -> dict:
    decision = validation_decision or "approved"
    notes = validation_notes or "auto"

    log.info(
        "erp_export_starting",
        document_id=document_id,
        validation_decision=decision,
        extraction_skipped=extraction_skipped,
    )

    if extraction_skipped:
        log.info("erp_export_skipped_no_extraction", document_id=document_id)
        return {"erp_status": "SKIPPED"}

    body = {"decision": decision, "notes": notes}

    async with core_client(timeout=85.0) as client:
        resp = await client.post(
            f"/api/ocr/documents/{document_id}/validate",
            json=body,
        )
        if resp.status_code == 422:
            log.info("erp_validate_skipped_no_extraction", document_id=document_id)
            return {"erp_status": "SKIPPED_NO_EXTRACTION"}
        resp.raise_for_status()
        data = resp.json()

    doc_status = (
        data.get("document", {}).get("status")
        or data.get("status")
        or decision.upper()
    )

    log.info("erp_export_done", document_id=document_id, doc_status=doc_status)
    return {"erp_status": doc_status}
