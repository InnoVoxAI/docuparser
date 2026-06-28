"""Worker for layout classification via layout-service."""
import structlog
from pyzeebe import ZeebeTaskRouter

from workers._http import layout_client

log = structlog.get_logger()

classify_layout = ZeebeTaskRouter()


@classify_layout.task(
    task_type="docuparse-classify-layout",
    timeout_ms=45_000,
    max_jobs_to_activate=5,
)
async def _classify_layout(
    document_id: str,
    raw_text_uri: str = "",
    document_type: str = "unknown",
    **kwargs,
) -> dict:
    log.info("layout_classify_starting", document_id=document_id, raw_text_uri=raw_text_uri)

    async with layout_client(timeout=40.0) as client:
        resp = await client.post(
            "/api/v1/classify-layout",
            json={
                "raw_text_uri": raw_text_uri,
                "document_type": document_type,
                "metadata": {"document_id": document_id},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    log.info(
        "layout_classified",
        document_id=document_id,
        layout=data.get("layout"),
        confidence=data.get("confidence"),
    )
    return {
        "layout": data.get("layout"),
        "layout_confidence": data.get("confidence"),
        "layout_requires_human_validation": data.get("requires_human_validation", False),
    }
