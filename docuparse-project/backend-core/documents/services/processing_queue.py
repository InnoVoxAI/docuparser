from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from django.db import connection

logger = logging.getLogger(__name__)

_MAX_WORKERS = int(os.environ.get("DOCUPARSE_PROCESSING_WORKERS", "2"))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS)


def _tenant_from_connection() -> object:
    """Return the real Tenant object from the current connection."""
    tenant = getattr(connection, "tenant", None)
    if tenant is None or not hasattr(tenant, "slug"):
        raise RuntimeError("No real tenant set on the connection — cannot submit background task.")
    return tenant


def submit_document_processing(document_id: int) -> None:
    tenant = _tenant_from_connection()
    _executor.submit(_run_processing_safely, document_id, tenant)


def _run_processing_safely(document_id: int, tenant: object) -> None:
    try:
        from documents.services.ocr_processor import process_document_ocr
        connection.set_tenant(tenant)
        process_document_ocr(document_id, tenant_slug=tenant.slug)
    except Exception as exc:
        logger.warning(
            "processing_queue_failed",
            exc_info=True,
            extra={"document_id": str(document_id), "tenant": getattr(tenant, "slug", "?"), "error": str(exc)},
        )


def submit_document_langextract(document_id, schema_config_id) -> None:
    tenant = _tenant_from_connection()
    _executor.submit(_run_langextract_safely, document_id, schema_config_id, tenant)


def _run_langextract_safely(document_id, schema_config_id, tenant: object) -> None:
    try:
        from documents.services.ocr_processor import run_langextract_for_document
        connection.set_tenant(tenant)
        run_langextract_for_document(document_id, schema_config_id)
    except Exception as exc:
        logger.warning(
            "langextract_queue_failed",
            exc_info=True,
            extra={"document_id": str(document_id), "tenant": getattr(tenant, "slug", "?"), "error": str(exc)},
        )
