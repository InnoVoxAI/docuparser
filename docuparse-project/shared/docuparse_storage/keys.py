from __future__ import annotations

from dataclasses import dataclass


DOCUMENT_ORIGINAL_KEY = "documents/{tenant_id}/{document_id}/original"
DOCUMENT_OCR_RAW_TEXT_KEY = "documents/{tenant_id}/{document_id}/ocr/raw_text.json"


@dataclass(frozen=True)
class StoredObject:
    uri: str
    key: str
    size_bytes: int
    sha256: str


def document_original_key(tenant_id: str, document_id: str) -> str:
    return DOCUMENT_ORIGINAL_KEY.format(tenant_id=tenant_id, document_id=document_id)


def document_ocr_raw_text_key(tenant_id: str, document_id: str) -> str:
    return DOCUMENT_OCR_RAW_TEXT_KEY.format(tenant_id=tenant_id, document_id=document_id)
