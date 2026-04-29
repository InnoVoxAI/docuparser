# =============================================================================
# BACKWARD-COMPAT SHIM — Fase 3 do refactor de arquitetura.
#
# A lógica foi movida para domain/classifier.py.
# Este arquivo existe apenas para não quebrar imports existentes, como:
#   from agent.classifier import classify_document, ...
#
# __all__ declara explicitamente que estes são re-exports intencionais,
# suprimindo hints de "symbol not accessed" no linter/type-checker.
#
# Será removido na Fase 7 (limpeza final).
# =============================================================================

from domain.classifier import (
    classify_document,
    get_engine_preprocessing_hints_for_class,
    CLASS_DIGITAL_PDF,
    CLASS_SCANNED_IMAGE,
    CLASS_HANDWRITTEN_COMPLEX,
    CLASSIFICATION_ENGINE_PREPROCESSING_HINTS,
)

__all__ = [
    "classify_document",
    "get_engine_preprocessing_hints_for_class",
    "CLASS_DIGITAL_PDF",
    "CLASS_SCANNED_IMAGE",
    "CLASS_HANDWRITTEN_COMPLEX",
    "CLASSIFICATION_ENGINE_PREPROCESSING_HINTS",
]
