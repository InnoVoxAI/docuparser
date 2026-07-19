"""Shared LayoutConfig/SchemaConfig resolution against backend-core.

Used by both the layout classification worker (to decide whether a document's
type already has a configured extraction template) and the extraction worker
(as a defense-in-depth fallback resolver).
"""
import structlog

from workers._http import core_client

log = structlog.get_logger()


async def resolve_schema_config_id(layout: str, document_type: str, tenant_id: str) -> str:
    """Look up the active schema config for this layout/document_type combination."""
    if not layout:
        return ""
    try:
        async with core_client(tenant_id, timeout=10.0) as client:
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
