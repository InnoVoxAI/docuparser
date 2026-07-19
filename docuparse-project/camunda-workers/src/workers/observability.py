"""Worker for recording a terminal processing failure.

Basic structured logging only (via structlog) — no observability platform
integration exists yet. The structured log line is available for whatever log
aggregation/observability tooling is stood up later.
"""
from datetime import datetime, timezone

import structlog
from pyzeebe import ZeebeTaskRouter

log = structlog.get_logger()

log_failure = ZeebeTaskRouter()


@log_failure.task(
    task_type="docuparse-log-failure",
    timeout_ms=10_000,
    max_jobs_to_activate=10,
)
async def _log_failure(
    document_id: str,
    tenant_id: str,
    failure_reason: str,
    ocr_retry_count: int = 0,
    failure_step: str = "",
    **kwargs,
) -> dict:
    logged_at = datetime.now(timezone.utc).isoformat()
    log.error(
        "docuparse_failure",
        document_id=document_id,
        tenant_id=tenant_id,
        failure_reason=failure_reason,
        failure_step=failure_step,
        retry_count=ocr_retry_count,
        logged_at=logged_at,
    )
    return {"logged_at": logged_at}
