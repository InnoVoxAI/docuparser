# =============================================================================
# BACKWARD-COMPAT SHIM — Fase 4 do refactor de arquitetura.
#
# A lógica foi movida para infrastructure/engines/docling_engine.py.
# Este arquivo existe apenas para não quebrar imports existentes, como:
#   from engines.docling_engine import DoclingEngine
#
# __all__ declara explicitamente que estes são re-exports intencionais,
# suprimindo hints de "symbol not accessed" no linter/type-checker.
#
# Será removido na Fase 7 (limpeza final).
# =============================================================================

from infrastructure.engines.docling_engine import DoclingEngine

__all__ = ["DoclingEngine"]
