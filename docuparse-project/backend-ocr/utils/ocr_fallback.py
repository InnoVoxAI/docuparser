# =============================================================================
# BACKWARD-COMPAT SHIM — Fase 4 do refactor de arquitetura.
#
# A lógica foi movida para infrastructure/fallback/fallback_handler.py.
# Este arquivo existe apenas para não quebrar imports existentes, como:
#   from utils.ocr_fallback import should_trigger_fallback, merge_fallback_result, ...
#
# __all__ declara explicitamente que estes são re-exports intencionais,
# suprimindo hints de "symbol not accessed" no linter/type-checker.
#
# Será removido na Fase 7 (limpeza final).
# =============================================================================

from infrastructure.fallback.fallback_handler import (
    should_trigger_fallback,
    is_engine_error_fallback,
    merge_fallback_result,
)

__all__ = [
    "should_trigger_fallback",
    "is_engine_error_fallback",
    "merge_fallback_result",
]
