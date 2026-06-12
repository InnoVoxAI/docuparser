from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_MAX_WORKERS = int(os.environ.get("DOCUPARSE_PROCESSING_WORKERS", "2"))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS)


def submit_document_processing(document_id: int) -> None:
    _executor.submit(_run_processing_safely, document_id)


def _run_processing_safely(document_id: int) -> None:
    try:
        from documents.services.ocr_processor import process_document_ocr
        process_document_ocr(document_id)
    except Exception as exc:
        logger.warning(
            "processing_queue_failed",
            extra={"document_id": str(document_id), "error": str(exc)},
        )


def submit_document_langextract(document_id, schema_config_id) -> None:
    _executor.submit(_run_langextract_safely, document_id, schema_config_id)


def _run_langextract_safely(document_id, schema_config_id) -> None:
    try:
        from documents.services.ocr_processor import run_langextract_for_document
        run_langextract_for_document(document_id, schema_config_id)
    except Exception as exc:
        logger.warning(
            "langextract_queue_failed",
            extra={"document_id": str(document_id), "error": str(exc)},
        )
