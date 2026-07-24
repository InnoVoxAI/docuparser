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
        raise RuntimeError(
            "No real tenant set on the connection — cannot submit background task."
        )
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
        # `last_step` aponta qual dependência caiu (storage_read/ocr_request/
        # storage_write) sem precisar correlacionar com as linhas `step=` acima.
        # Causa no corpo da mensagem, não em `extra`: o formatter padrão não
        # renderiza campos de `extra`, então isto emitia só o próprio nome.
        try:
            from documents.services.ocr_processor import current_step

            last_step = current_step()
        except Exception:
            last_step = "unknown"
        logger.warning(
            "processing_queue_failed | document_id=%s | tenant=%s | last_step=%s | error_type=%s | error=%s",
            document_id,
            getattr(tenant, "slug", "?"),
            last_step,
            type(exc).__name__,
            exc,
            exc_info=True,
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
            "langextract_queue_failed | document_id=%s | tenant=%s | error_type=%s | error=%s",
            document_id,
            getattr(tenant, "slug", "?"),
            type(exc).__name__,
            exc,
            exc_info=True,
        )
