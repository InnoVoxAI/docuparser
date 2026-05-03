from __future__ import annotations

import json
import logging
from io import BytesIO

from django.conf import settings
from django.utils import timezone

from docuparse_storage import LocalStorage, document_ocr_raw_text_key

from documents.models import Document, ExtractionResult
from documents.services.ocr_client import OCRClient

logger = logging.getLogger(__name__)


def process_document_ocr(document_id) -> Document:
    document = Document.objects.select_related("tenant").get(id=document_id)
    content = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR).get_bytes(document.file_uri)
    result = OCRClient().process_document(
        BytesIO(content),
        document.original_filename or f"{document.id}.pdf",
        legacy_extraction=True,
    )

    raw_text = result.get("raw_text") or result.get("raw_text_fallback") or ""
    raw_text_payload = {
        "raw_text": raw_text,
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

    fields = _clean_extracted_fields(result.get("fields") or {})
    ExtractionResult.objects.update_or_create(
        document=document,
        defaults={
            "schema_id": "legacy_ocr",
            "schema_version": "v1",
            "fields": fields,
            "confidence": result.get("final_score") or 0.0,
            "requires_human_validation": True,
        },
    )
    document.raw_text_uri = stored.uri
    document.document_type = result.get("document_type", "") or document.document_type
    document.status = Document.Status.VALIDATION_PENDING
    document.save(update_fields=["raw_text_uri", "document_type", "status", "updated_at"])
    return document


def start_document_ocr_thread(document_id) -> None:
    import threading

    thread = threading.Thread(target=_run_ocr_safely, args=(document_id,), daemon=True)
    thread.start()


def _run_ocr_safely(document_id) -> None:
    try:
        process_document_ocr(document_id)
    except Exception as exc:
        logger.warning("automatic_ocr_failed", extra={"document_id": str(document_id), "error": str(exc)})


def _clean_extracted_fields(fields: dict) -> dict:
    cleaned = {}
    for key, value in fields.items():
        if value in ("", None, [], {}):
            continue
        text_value = str(value)
        if key == "retencao" and len(text_value) > 300:
            continue
        cleaned[key] = value
    return cleaned
