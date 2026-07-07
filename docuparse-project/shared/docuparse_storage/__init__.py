"""Camada de storage de objetos compartilhada entre os backends.

Backends disponíveis:
  - ``LocalStorage``: disco local (comportamento histórico, default).
  - ``S3Storage``: MinIO/S3-compatível (ambiente integrado).
  - ``RoutingStorage``: escreve no backend configurado e lê despachando pelo
    esquema da URI (``local://`` vs ``s3://``), habilitando coexistência,
    migração incremental e rollback.

Use ``get_storage()`` como único ponto de instanciação no código de aplicação;
o backend é selecionado por variável de ambiente (default ``local``).
"""

from __future__ import annotations

from .base import Storage
from .factory import get_storage
from .keys import (
    DOCUMENT_OCR_RAW_TEXT_KEY,
    DOCUMENT_ORIGINAL_KEY,
    StoredObject,
    document_ocr_raw_text_key,
    document_original_key,
)
from .local import LocalStorage
from .routing import RoutingStorage
from .s3 import S3Storage

__all__ = [
    "Storage",
    "StoredObject",
    "LocalStorage",
    "S3Storage",
    "RoutingStorage",
    "get_storage",
    "DOCUMENT_ORIGINAL_KEY",
    "DOCUMENT_OCR_RAW_TEXT_KEY",
    "document_original_key",
    "document_ocr_raw_text_key",
]
