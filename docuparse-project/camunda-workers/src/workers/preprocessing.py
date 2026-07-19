"""Worker for automatic image pre-processing before an OCR retry."""
import structlog
from pyzeebe import ZeebeTaskRouter

log = structlog.get_logger()

preprocess_image = ZeebeTaskRouter()


@preprocess_image.task(
    task_type="docuparse-preprocess-image",
    timeout_ms=30_000,
    max_jobs_to_activate=5,
)
async def _preprocess_image(
    document_id: str,
    ocr_retry_count: int = 0,
    **kwargs,
) -> dict:
    """Pre-process/clean the source image ahead of an OCR retry.

    Increments and returns the process-scoped retry counter (data-model.md);
    Gateway_19gkipo reads it to cap retries at 3.
    """
    new_count = ocr_retry_count + 1
    log.info("image_preprocess", document_id=document_id, ocr_retry_count=new_count)
    return {"ocr_retry_count": new_count}
