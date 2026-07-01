"""Worker for programmatic document validation (approve/reject/correct) via backend-core.

For human-driven validation use a <userTask> in the BPMN instead — Tasklist handles it.
This worker handles automated or post-human-task programmatic decisions.
"""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import core_client

log = structlog.get_logger()

validate_document = ZeebeTaskRouter()


@validate_document.task(
    task_type="docuparse-validate-document",
    timeout_ms=15_000,
    max_jobs_to_activate=10,
)
async def _validate_document(
    document_id: str,
    decision: str,
    notes: str = "",
    corrected_fields: dict | None = None,
    decided_by_id: str | None = None,
    **kwargs,
) -> dict:
    """Submit a validation decision to backend-core.

    decision: "approved" | "rejected" | "corrected"
    notes: required when decision == "rejected"
    corrected_fields: dict of field overrides when decision == "corrected"

    Typical BPMN usage:
    - After a <userTask>, map the task form output to these input variables,
      then use this worker to persist the decision.
    - For fully automated approval flows, hardcode decision="approved" via
      a BPMN <zeebe:input source="=\"approved\"" target="decision"/>.
    """
    body: dict = {"decision": decision, "notes": notes}
    if corrected_fields:
        body["corrected_fields"] = corrected_fields
    if decided_by_id:
        body["decided_by_id"] = decided_by_id

    async with core_client(timeout=12.0) as client:
        resp = await client.post(
            f"/api/ocr/documents/{document_id}/validate",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    log.info(
        "validation_recorded",
        document_id=document_id,
        decision=decision,
    )
    return {
        "doc_status": data.get("document", {}).get("status") or data.get("status"),
        "validation_decision": decision,
    }
