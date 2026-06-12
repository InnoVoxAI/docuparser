from __future__ import annotations

import json
import logging
from io import BytesIO

from django.conf import settings
from django.utils import timezone

from docuparse_storage import LocalStorage, document_ocr_raw_text_key

from documents.models import Document, ExtractionResult, LayoutConfig, SchemaConfig
from documents.services.ocr_client import OCRClient
from documents.services.langextract_client import LangExtractClient

logger = logging.getLogger(__name__)


def process_document_ocr(document_id) -> Document:
    document = Document.objects.select_related("tenant").get(id=document_id)
    content = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR).get_bytes(document.file_uri)
    result = OCRClient().process_document(
        BytesIO(content),
        document.original_filename or f"{document.id}.pdf",
        legacy_extraction=False,
    )

    raw_text = result.get("raw_text") or result.get("raw_text_fallback") or ""
    raw_text_formatted = result.get("raw_text_formatted", "")

    logger.info(
        "ocr_processor: raw_text_formatted storing | document_id=%s | chars=%d | preview=%r",
        document_id,
        len(raw_text_formatted),
        raw_text_formatted[:300],
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
            "classification_engine_preprocessing_hints": result.get("classification_engine_preprocessing_hints", {}),
        },
        "processed_at": timezone.now().isoformat(),
    }
    stored = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR).put_bytes(
        document_ocr_raw_text_key(document.tenant.slug, str(document.id)),
        json.dumps(raw_text_payload, ensure_ascii=False).encode("utf-8"),
    )

    document.raw_text_uri = stored.uri
    document.document_type = result.get("document_type", "") or document.document_type
    document.status = Document.Status.OCR_COMPLETED
    document.save(update_fields=["raw_text_uri", "document_type", "status", "updated_at"])
    auto_extract_after_ocr(document)
    return document


def auto_extract_after_ocr(document: Document) -> None:
    if not settings.DOCUPARSE_AUTO_PROCESS_EXTRACTION:
        return
    if not document.raw_text_uri:
        return

    try:
        storage = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR)
        payload = json.loads(storage.get_bytes(document.raw_text_uri).decode("utf-8"))
        raw_text = str(payload.get("raw_text") or "")
    except Exception as exc:
        logger.warning("auto_extract_failed_reading_text", extra={"document_id": str(document.id), "error": str(exc)})
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
        return

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
                "requires_human_validation": result.get("requires_human_validation", True),
            },
        )
        document.transition_to(Document.Status.VALIDATION_PENDING)
    except Exception as exc:
        logger.warning("auto_extract_failed", extra={"document_id": str(document.id), "error": str(exc)})


def run_langextract_for_document(document_id, schema_config_id) -> dict:
    """On-demand LLM extraction for a chosen SchemaConfig.

    Runs off the HTTP request path (see processing_queue.submit_document_langextract):
    the LLM call can take many seconds, and awaiting it inline holds the connection open
    long enough for the production gateway to return a 502 (without CORS headers).
    """
    document = Document.objects.get(id=document_id)
    schema_config = SchemaConfig.objects.get(id=schema_config_id)

    storage = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR)
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
            "requires_human_validation": result.get("requires_human_validation", True),
        },
    )
    if document.status not in (
        Document.Status.VALIDATION_PENDING,
        Document.Status.APPROVED,
        Document.Status.REJECTED,
    ):
        document.transition_to(Document.Status.EXTRACTION_COMPLETED)
    return result


def _classify_raw_text(raw_text: str) -> str | None:
    """Returns the schema_id that best matches the document text, or None."""
    import models.nota_fiscal.schemas as _nf
    import models.contadeagua.schemas as _agua
    import models.boleto.schemas as _boleto

    if _nf.is_likely(raw_text):
        return _nf.SCHEMA_ID
    if _agua.is_likely(raw_text):
        return _agua.SCHEMA_ID
    if _boleto.is_likely(raw_text):
        return _boleto.SCHEMA_ID
    return None


def _resolve_schema_for_extraction(document: Document, raw_text: str) -> SchemaConfig | None:
    """
    Priority:
    1. Explicit LayoutConfig via document.layout (admin-configured)
    2. Text-based classifier — mirrors classify_text_view heuristic
    3. LayoutConfig by document.document_type (fallback for custom schemas)
    """
    if document.layout:
        cfg = (
            LayoutConfig.objects.filter(layout=document.layout, tenant=document.tenant, is_active=True)
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
            LayoutConfig.objects.filter(document_type=document.document_type, tenant=document.tenant, is_active=True)
            .select_related("schema_config")
            .first()
        )
        if cfg and cfg.schema_config:
            return cfg.schema_config

    return None


def start_document_ocr_thread(document_id) -> None:
    import threading

    thread = threading.Thread(target=_run_ocr_safely, args=(document_id,), daemon=True)
    thread.start()


def _run_ocr_safely(document_id) -> None:
    try:
        process_document_ocr(document_id)
    except Exception as exc:
        logger.warning("automatic_ocr_failed", extra={"document_id": str(document_id), "error": str(exc)})


