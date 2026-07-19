"""Worker for notifying the submitter of a terminal processing failure."""
import structlog
from pyzeebe import ZeebeTaskRouter

log = structlog.get_logger()

notify_user = ZeebeTaskRouter()


@notify_user.task(
    task_type="docuparse-notify-user",
    timeout_ms=15_000,
    max_jobs_to_activate=10,
)
async def _notify_user(
    document_id: str,
    rejection_reason: str,
    channel: str = "manual",
    **kwargs,
) -> dict:
    """Notify the submitter that their document could not be processed.

    Human-readable, actionable message only (constitution: no stack traces/raw
    exception text) — `rejection_reason` must already be a short user-facing string.
    """
    log.info(
        "notify_user",
        document_id=document_id,
        rejection_reason=rejection_reason,
        channel=channel,
    )
    return {"notified": True}
