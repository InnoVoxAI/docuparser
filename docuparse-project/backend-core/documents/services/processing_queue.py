from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from django.db import connection
from docuparse_observability.tracing import capture_current_span_link
from docuparse_orchestrator.context import orchestration_run
from opentelemetry import trace

logger = logging.getLogger(__name__)

_MAX_WORKERS = int(os.environ.get("DOCUPARSE_PROCESSING_WORKERS", "2"))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS)
_tracer = trace.get_tracer(__name__)


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
    link = capture_current_span_link()
    _executor.submit(_run_document_processing, document_id, tenant, link)


def _run_document_processing(document_id: int, tenant: object, link: trace.Link | None) -> None:
    connection.set_tenant(tenant)
    from documents.services.ocr_processor import extraction_task, ocr_task

    # orchestration_run marca o run como FAILED sozinho quando qualquer @task
    # chamado aqui dentro termina em erro (ver context.py) — não precisa de
    # raise manual pra sinalizar isso; só o "return" natural pra não seguir
    # pra próxima etapa.
    with orchestration_run(
        "document_processing", link=link, document_id=str(document_id)
    ):
        result = ocr_task(document_id, tenant_slug=tenant.slug)
        if result.status == "error":
            logger.warning(
                "document_processing_failed | document_id=%s | tenant=%s | step=ocr | error=%s",
                document_id,
                getattr(tenant, "slug", "?"),
                result.error.message,
            )
            return

        result = extraction_task(document_id)
        if result.status == "error":
            logger.warning(
                "document_processing_failed | document_id=%s | tenant=%s | step=extraction | error=%s",
                document_id,
                getattr(tenant, "slug", "?"),
                result.error.message,
            )


def submit_document_langextract(document_id, schema_config_id) -> None:
    tenant = _tenant_from_connection()
    link = capture_current_span_link()
    _executor.submit(_run_langextract_safely, document_id, schema_config_id, tenant, link)


def _run_langextract_safely(
    document_id, schema_config_id, tenant: object, link: trace.Link | None
) -> None:
    with _tracer.start_as_current_span(
        "document.langextract_processing", links=[link] if link else []
    ) as span:
        try:
            from documents.services.ocr_processor import run_langextract_for_document

            connection.set_tenant(tenant)
            run_langextract_for_document(document_id, schema_config_id)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            logger.warning(
                "langextract_queue_failed | document_id=%s | tenant=%s | error_type=%s | error=%s",
                document_id,
                getattr(tenant, "slug", "?"),
                type(exc).__name__,
                exc,
                exc_info=True,
            )
