# =============================================================================
# BACKWARD-COMPAT SHIM — Fase 4 do refactor de arquitetura.
#
# A lógica foi movida para infrastructure/engines/trocr_engine.py.
# Este arquivo existe apenas para não quebrar imports existentes, como:
#   from engines.trocr_engine import TrOCREngine
#
# __all__ declara explicitamente que estes são re-exports intencionais,
# suprimindo hints de "symbol not accessed" no linter/type-checker.
#
# Será removido na Fase 7 (limpeza final).
# =============================================================================

from infrastructure.engines.trocr_engine import TrOCREngine

__all__ = ["TrOCREngine"]
