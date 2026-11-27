from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, connection
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


def _with_fresh_connection(fn, *args) -> None:
    """Roda `fn` numa thread do pool com uma conexão válida com o banco.

    O Django só renova conexões no ciclo de uma requisição HTTP (sinais
    request_started/request_finished). Nas threads deste pool, a conexão
    aberta na primeira tarefa ficava para sempre: quando o Postgres
    reiniciava, toda tarefa seguinte falhava ao gravar o run, sem log, e o
    documento ficava parado. Por isso cada tarefa descarta a conexão
    inutilizável antes de começar e fecha a sua ao terminar.
    """
    close_old_connections()
    try:
        fn(*args)
    finally:
        connection.close()


def submit_document_processing(document_id: int) -> None:
    tenant = _tenant_from_connection()
    link = capture_current_span_link()
    _executor.submit(
        _with_fresh_connection,
        _run_document_processing_safely,
        document_id,
        tenant,
        link,
    )


def _run_document_processing_safely(
    document_id, tenant: object, link: trace.Link | None
) -> None:
    """Registra qualquer exceção da tarefa e marca o documento como falho.

    O ThreadPoolExecutor guarda a exceção num Future que ninguém lê: sem este
    try/except a falha some e o frontend consulta o status para sempre.
    """
    from documents.services.ocr_processor import current_step, reset_step

    reset_step()
    try:
        _run_document_processing(document_id, tenant, link)
    except Exception as exc:
        logger.exception(
            "processing_queue_failed | document_id=%s | tenant=%s | last_step=%s | error_type=%s | error=%s",
            document_id,
            getattr(tenant, "slug", "?"),
            current_step(),
            type(exc).__name__,
            exc,
        )
        _mark_document_failed(document_id, tenant, exc)


def _mark_document_failed(document_id, tenant: object, exc: Exception) -> None:
    """Tira o documento de RECEIVED para OCR_FAILED, para ele sair da fila na
    tela e poder ser reprocessado. Não mexe em documentos que já avançaram."""
    from documents.services.processing_recovery import mark_received_document_failed

    try:
        # A exceção pode ter vindo de uma conexão morta: troca por uma nova.
        close_old_connections()
        connection.set_tenant(tenant)
        mark_received_document_failed(
            document_id, error_type=type(exc).__name__, error=str(exc)
        )
    except Exception:
        logger.exception(
            "processing_queue_mark_failed_error | document_id=%s | tenant=%s",
            document_id,
            getattr(tenant, "slug", "?"),
        )


def _run_document_processing(
    document_id: int, tenant: object, link: trace.Link | None
) -> None:
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
    _executor.submit(
        _with_fresh_connection,
        _run_langextract_safely,
        document_id,
        schema_config_id,
        tenant,
        link,
    )


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


def submit_erp_dispatch(event_payload: dict) -> None:
    """Roda o conector do ERP fora da requisição: ele faz chamadas de rede ao Superlógica."""
    tenant = _tenant_from_connection()
    link = capture_current_span_link()
    _executor.submit(
        _with_fresh_connection, _run_erp_dispatch, event_payload, tenant, link
    )


def _run_erp_dispatch(
    event_payload: dict, tenant: object, link: trace.Link | None
) -> None:
    connection.set_tenant(tenant)
    with _tracer.start_as_current_span("erp.dispatch", links=[link] if link else []):
        try:
            from documents.services.event_consumers import (
                consume_erp_integration_requested,
            )

            consume_erp_integration_requested(event_payload)
        except Exception as exc:
            # Só o tipo do erro: nada do pedido nem da resposta do ERP vai ao log.
            logger.error(
                "erp_dispatch_failed | document_id=%s | tenant=%s | error=%s",
                event_payload.get("document_id"),
                getattr(tenant, "slug", "?"),
                type(exc).__name__,
            )
