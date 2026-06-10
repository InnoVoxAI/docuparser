"""Client that fetches LayoutConfig + SchemaConfig definitions from backend-core.

The langextract-service is stateless and does not have direct database access.
When a layout.classified event arrives, this module is called to discover which
SchemaConfig (prompt + field list) should be used for the tenant + layout pair.

Environment variables:
    BACKEND_CORE_URL              — base URL of the backend-core service
                                    (default: http://127.0.0.1:8000)
    DOCUPARSE_INTERNAL_SERVICE_TOKEN — bearer token for internal service calls
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def fetch_schema_for_layout(
    tenant_id: str,
    layout: str,
    document_type: str,
) -> tuple[dict[str, Any] | None, float]:
    """Return (schema_definition, confidence_threshold) for the given layout.

    Returns (None, 0.75) when:
    - backend-core is unreachable
    - no active LayoutConfig matches the layout
    - the matched SchemaConfig has an empty definition
    """
    backend_core_url = os.getenv("BACKEND_CORE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    internal_token = os.getenv("DOCUPARSE_INTERNAL_SERVICE_TOKEN", "").strip()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if internal_token:
        headers["Authorization"] = f"Bearer {internal_token}"

    # --- Step 1: fetch all active LayoutConfigs ---
    try:
        layout_configs: list[dict] = _get_json(
            f"{backend_core_url}/api/ocr/layout-configs", headers
        )
    except Exception as exc:
        logger.warning(
            "langextract.backend_core_client.layout_configs_fetch_failed | "
            "tenant=%s layout=%s error=%s",
            tenant_id, layout, exc,
        )
        return None, 0.75

    # --- Step 2: find the best matching LayoutConfig ---
    # Primary match: layout + document_type + active
    matching = next(
        (
            c for c in layout_configs
            if c.get("layout") == layout
            and c.get("document_type") == document_type
            and c.get("is_active")
        ),
        None,
    )
    # Secondary match: layout only (ignore document_type)
    if matching is None:
        matching = next(
            (c for c in layout_configs if c.get("layout") == layout and c.get("is_active")),
            None,
        )

    if matching is None:
        logger.info(
            "langextract.backend_core_client.no_layout_config | "
            "tenant=%s layout=%s document_type=%s",
            tenant_id, layout, document_type,
        )
        return None, 0.75

    schema_config_id = matching.get("schema_config_id")
    confidence_threshold = float(matching.get("confidence_threshold") or 0.75)

    if not schema_config_id:
        logger.info(
            "langextract.backend_core_client.layout_config_has_no_schema | "
            "tenant=%s layout=%s",
            tenant_id, layout,
        )
        return None, confidence_threshold

    # --- Step 3: fetch the SchemaConfig definition ---
    try:
        schema_config: dict = _get_json(
            f"{backend_core_url}/api/ocr/schema-configs/{schema_config_id}", headers
        )
    except Exception as exc:
        logger.warning(
            "langextract.backend_core_client.schema_config_fetch_failed | "
            "schema_config_id=%s error=%s",
            schema_config_id, exc,
        )
        return None, confidence_threshold

    definition = schema_config.get("definition")
    if not definition or not isinstance(definition, dict):
        logger.info(
            "langextract.backend_core_client.empty_schema_definition | "
            "schema_config_id=%s schema_id=%s",
            schema_config_id, schema_config.get("schema_id"),
        )
        return None, confidence_threshold

    logger.info(
        "langextract.backend_core_client.schema_loaded | "
        "schema_id=%s layout=%s document_type=%s tenant=%s",
        schema_config.get("schema_id"), layout, document_type, tenant_id,
    )
    return definition, confidence_threshold


def _get_json(url: str, headers: dict[str, str]) -> Any:
    """Perform a GET request and return the parsed JSON body."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))
