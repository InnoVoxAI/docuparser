from __future__ import annotations

import json
import logging
import threading
import time
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from docuparse_observability.tracing import capture_current_span_link
from docuparse_orchestrator.decorators import task
from docuparse_storage import document_ocr_raw_text_key, get_storage
from opentelemetry import trace

from documents.models import Document, ExtractionResult, LayoutConfig, SchemaConfig
from documents.services.langextract_client import LangExtractClient
from documents.services.ocr_client import OCRClient

logger = logging.getLogger(__name__)

# Etapa corrente por thread. process_document_ocr roda numa thread do
# ThreadPoolExecutor e toda exceção vira um único `processing_queue_failed`;
# guardar a etapa aqui deixa o chamador anexar `last_step=` à linha do erro sem
# precisar correlacionar com as linhas `step=` acima. threading.local isola cada
# thread; process_document_ocr reseta no início (as threads do pool são reusadas).
_progress = threading.local()


def current_step() -> str:
    """Última etapa alcançada por process_document_ocr nesta thread."""
    return getattr(_progress, "step", "not_started")


def _log_step(step: str, document_id, tenant_slug: str, schema: str, **fields) -> None:
    """Marca uma etapa do pipeline de OCR.

    A última etapa logada antes de um `processing_queue_failed` diz qual
    dependência caiu (storage de leitura, backend-ocr, storage de escrita). Os
    valores saem com ``repr()`` porque é o que expõe aspas/espaços vindos de env.
    """
    _progress.step = step
    detail = " | ".join(f"{key}={value!r}" for key, value in fields.items())
    logger.info(
        "ocr_processor: step=%s | document_id=%s | tenant=%s | schema=%s | %s",
        step,
        document_id,
        tenant_slug,
        schema,
        detail,
    )


def process_document_ocr(document_id, tenant_slug: str | None = None) -> Document:
    from django.db import connection as _conn

    # Reset antes de qualquer trabalho: se a exceção vier daqui (ex.: documento
    # inexistente, tenant/schema errado) o last_step reflete esta execução, não a
    # anterior desta thread reusada do pool.
    _progress.step = "load_document"
    document = Document.objects.get(id=document_id)
    if not tenant_slug:
        # Fallback: derive from schema name when called directly (e.g. tests, management commands)
        schema_name = _conn.schema_name or "public"
        tenant_slug = (
            schema_name.removeprefix("tenant_") if schema_name != "public" else "public"
        )

    _log_step(
        "storage_read",
        document_id,
        tenant_slug,
        _conn.schema_name,
        file_uri=document.file_uri,
    )
    content = get_storage().get_bytes(document.file_uri)

    _log_step(
        "ocr_request",
        document_id,
        tenant_slug,
        _conn.schema_name,
        url=settings.BACKEND_OCR_URL,
        size_bytes=len(content),
    )
    result = OCRClient().process_document(
        BytesIO(content),
        document.original_filename or f"{document.id}.pdf",
        legacy_extraction=False,
    )

    raw_text = result.get("raw_text") or result.get("raw_text_fallback") or ""
    raw_text_formatted = result.get("raw_text_formatted", "")

    _log_step(
        "storage_write",
        document_id,
        tenant_slug,
        _conn.schema_name,
        engine=result.get("engine_used", "unknown"),
        raw_text_chars=len(raw_text),
        formatted_chars=len(raw_text_formatted),
        formatted_preview=raw_text_formatted[:200],
    )

    raw_text_payload = {
        "raw_text": raw_text,
        "raw_text_formatted": raw_text_formatted,
        "document_type": result.get("document_type", "unknown"),
        "engine_used": result.get("engine_used", "unknown"),
        "ocr": {
            "engine_used": result.get("engine_used", "unknown"),
            "classification": result.get("document_type", "unknown"),
            "preprocessing_hint": result.get("preprocessing_hint", ""),
            "classification_engine_preprocessing_hints": result.get(
                "classification_engine_preprocessing_hints", {}
            ),
        },
        "processed_at": timezone.now().isoformat(),
    }
    stored = get_storage().put_bytes(
        document_ocr_raw_text_key(tenant_slug, str(document.id)),
        json.dumps(raw_text_payload, ensure_ascii=False).encode("utf-8"),
    )

    document.raw_text_uri = stored.uri
    document.document_type = result.get("document_type", "") or document.document_type
    document.status = Document.Status.OCR_COMPLETED
    document.save(
        update_fields=["raw_text_uri", "document_type", "status", "updated_at"]
    )
    _log_step(
        "ocr_completed",
        document_id,
        tenant_slug,
        _conn.schema_name,
        raw_text_uri=stored.uri,
    )
    return document


def _ocr_task_body(document_id, tenant_slug: str | None = None) -> dict:
    document = process_document_ocr(document_id, tenant_slug=tenant_slug)
    # Uma referência (URI), não o texto bruto inteiro — evita inflar a linha
    # de TaskExecution com um blob potencialmente grande; quem quiser o texto
    # completo lê de storage por esse URI.
    return {
        "document_id": str(document.id),
        "document_type": document.document_type,
        "raw_text_uri": document.raw_text_uri,
    }


# Wrapper decorado usado pelo orquestrador (processing_queue.py) — retry +
# tracing + persistência em cima da mesma lógica de `process_document_ocr`,
# que continua chamável diretamente (sem retry) pelos endpoints de
# reprocessamento manual em views.py.
ocr_task = task("ocr")(_ocr_task_body)


def _record_extraction(document: Document, state: str, **details) -> None:
    """Persist the extraction lifecycle into document.metadata['extraction'].

    Makes pipeline failures visible in the UI and queryable in the DB instead of being
    swallowed by a logger.warning. States: running | completed | failed | pending_no_schema.
    """
    meta = dict(document.metadata or {})
    extraction = dict(meta.get("extraction") or {})
    extraction["state"] = state
    extraction["updated_at"] = timezone.now().isoformat()
    extraction["service_url"] = getattr(settings, "LANGEXTRACT_SERVICE_URL", "")
    for key, value in details.items():
        if value is not None:
            extraction[key] = value
    meta["extraction"] = extraction
    document.metadata = meta
    document.save(update_fields=["metadata", "updated_at"])


def auto_extract_after_ocr(document: Document) -> None:
    if not settings.DOCUPARSE_AUTO_PROCESS_EXTRACTION:
        return
    if not document.raw_text_uri:
        return

    try:
        storage = get_storage()
        payload = json.loads(storage.get_bytes(document.raw_text_uri).decode("utf-8"))
        raw_text = str(payload.get("raw_text") or "")
    except Exception as exc:
        logger.warning(
            "auto_extract_failed_reading_text",
            extra={"document_id": str(document.id), "error": str(exc)},
        )
        return

    if not raw_text.strip():
        return

    schema_config = _resolve_schema_for_extraction(document, raw_text)
    if not schema_config:
        logger.warning(
            "auto_extract_skipped_no_schema",
            extra={
                "document_id": str(document.id),
                "layout": document.layout,
                "document_type": document.document_type,
            },
        )
        _record_extraction(
            document,
            "pending_no_schema",
            layout=document.layout,
            document_type=document.document_type,
            trigger="auto",
        )
        return

    started = time.monotonic()
    _record_extraction(
        document, "running", schema_id=schema_config.schema_id, trigger="auto"
    )
    try:
        definition = {
            **schema_config.definition,
            "schema_id": schema_config.schema_id,
            "version": schema_config.version,
        }
        result = LangExtractClient().extract_with_schema(
            raw_text=raw_text,
            schema_definition=definition,
            layout=document.layout or "generic",
            document_type=str(document.content_type or "unknown"),
        )
        ExtractionResult.objects.update_or_create(
            document=document,
            defaults={
                "schema_id": result.get("schema_id") or schema_config.schema_id,
                "schema_version": result.get("schema_version") or schema_config.version,
                "fields": result.get("fields") or {},
                "confidence": result.get("confidence") or 0.0,
                "requires_human_validation": result.get(
                    "requires_human_validation", True
                ),
            },
        )
        _record_extraction(
            document,
            "completed",
            schema_id=schema_config.schema_id,
            duration_ms=int((time.monotonic() - started) * 1000),
            confidence=result.get("confidence"),
            trigger="auto",
        )
        document.transition_to(Document.Status.VALIDATION_PENDING)
    except Exception as exc:
        logger.error(
            "auto_extract_failed",
            exc_info=True,
            extra={
                "document_id": str(document.id),
                "schema_id": schema_config.schema_id,
                "service_url": LangExtractClient().base_url,
                "error": str(exc),
            },
        )
        _record_extraction(
            document,
            "failed",
            schema_id=schema_config.schema_id,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=int((time.monotonic() - started) * 1000),
            trigger="auto",
        )
        # Propaga para quem chama poder reagir (o @task abaixo precisa da
        # exceção pra contar como falha/retry; chamadores que preferem o
        # comportamento antigo — nunca levantar — devem envolver a chamada em
        # try/except, como as views de reprocessamento manual passam a fazer.
        raise


def _extraction_task_body(document_id) -> dict:
    document = Document.objects.get(id=document_id)
    auto_extract_after_ocr(document)
    payload = {"document_id": str(document.id)}
    extraction_result = ExtractionResult.objects.filter(document=document).first()
    if extraction_result:
        payload.update(
            {
                "schema_id": extraction_result.schema_id,
                "confidence": extraction_result.confidence,
                "fields": extraction_result.fields,
            }
        )
    return payload


# Wrapper decorado usado pelo orquestrador (processing_queue.py) — mesma
# lógica de `auto_extract_after_ocr`, com retry + tracing + persistência.
extraction_task = task("extraction")(_extraction_task_body)


def run_langextract_for_document(document_id, schema_config_id) -> dict:
    """On-demand LLM extraction for a chosen SchemaConfig.

    Runs off the HTTP request path (see processing_queue.submit_document_langextract):
    the LLM call can take many seconds, and awaiting it inline holds the connection open
    long enough for the production gateway to return a 502 (without CORS headers).
    """
    document = Document.objects.get(id=document_id)
    schema_config = SchemaConfig.objects.get(id=schema_config_id)
    started = time.monotonic()
    _record_extraction(
        document, "running", schema_id=schema_config.schema_id, trigger="manual"
    )

    try:
        storage = get_storage()
        payload = json.loads(storage.get_bytes(document.raw_text_uri).decode("utf-8"))
        raw_text = str(payload.get("raw_text") or "")
        if not raw_text.strip():
            raise ValueError("document raw text is empty")

        definition = {
            **schema_config.definition,
            "schema_id": schema_config.schema_id,
            "version": schema_config.version,
        }
        result = LangExtractClient().extract_with_schema(
            raw_text=raw_text,
            schema_definition=definition,
            layout=document.layout or "generic",
            document_type=str(document.content_type or "unknown"),
        )
        ExtractionResult.objects.update_or_create(
            document=document,
            defaults={
                "schema_id": result.get("schema_id") or schema_config.schema_id,
                "schema_version": result.get("schema_version") or schema_config.version,
                "fields": result.get("fields") or {},
                "confidence": result.get("confidence") or 0.0,
                "requires_human_validation": result.get(
                    "requires_human_validation", True
                ),
            },
        )
        if document.status not in (
            Document.Status.VALIDATION_PENDING,
            Document.Status.APPROVED,
            Document.Status.REJECTED,
        ):
            document.transition_to(Document.Status.EXTRACTION_COMPLETED)
        _record_extraction(
            document,
            "completed",
            schema_id=schema_config.schema_id,
            duration_ms=int((time.monotonic() - started) * 1000),
            confidence=result.get("confidence"),
            trigger="manual",
        )
        return result
    except Exception as exc:
        logger.error(
            "langextract_failed",
            exc_info=True,
            extra={
                "document_id": str(document_id),
                "schema_id": schema_config.schema_id,
                "service_url": LangExtractClient().base_url,
                "error": str(exc),
            },
        )
        _record_extraction(
            document,
            "failed",
            schema_id=schema_config.schema_id,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=int((time.monotonic() - started) * 1000),
            trigger="manual",
        )
        raise


def _classify_raw_text(raw_text: str) -> str | None:
    """Returns the schema_id that best matches the document text, or None."""
    import models.boleto.schemas as _boleto
    import models.contadeagua.schemas as _agua
    import models.nota_fiscal.schemas as _nf

    if _nf.is_likely(raw_text):
        return _nf.SCHEMA_ID
    if _agua.is_likely(raw_text):
        return _agua.SCHEMA_ID
    if _boleto.is_likely(raw_text):
        return _boleto.SCHEMA_ID
    return None


def _resolve_schema_for_extraction(
    document: Document, raw_text: str
) -> SchemaConfig | None:
    """
    Priority:
    1. Explicit LayoutConfig via document.layout (admin-configured)
    2. Text-based classifier — mirrors classify_text_view heuristic
    3. LayoutConfig by document.document_type (fallback for custom schemas)
    """
    if document.layout:
        cfg = (
            LayoutConfig.objects.filter(layout=document.layout, is_active=True)
            .select_related("schema_config")
            .first()
        )
        if cfg and cfg.schema_config:
            return cfg.schema_config

    schema_id = _classify_raw_text(raw_text)
    if schema_id:
        sc = SchemaConfig.objects.filter(schema_id=schema_id, is_active=True).first()
        if sc:
            return sc

    if document.document_type:
        cfg = (
            LayoutConfig.objects.filter(
                document_type=document.document_type, is_active=True
            )
            .select_related("schema_config")
            .first()
        )
        if cfg and cfg.schema_config:
            return cfg.schema_config

    return None


_tracer = trace.get_tracer(__name__)


def start_document_ocr_thread(document_id) -> None:
    import threading

    # threading.Thread não herda contextvars — sem capturar/propagar o Link
    # aqui, o processamento em background perde a associação com o trace de
    # origem (mesmo motivo de processing_queue.py, FR-007).
    link = capture_current_span_link()
    thread = threading.Thread(
        target=_run_ocr_safely, args=(document_id, link), daemon=True
    )
    thread.start()


def _run_ocr_safely(document_id, link: trace.Link | None = None) -> None:
    with _tracer.start_as_current_span(
        "document.ocr_processing", links=[link] if link else []
    ) as span:
        try:
            process_document_ocr(document_id)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            logger.warning(
                "automatic_ocr_failed",
                extra={"document_id": str(document_id), "error": str(exc)},
            )
