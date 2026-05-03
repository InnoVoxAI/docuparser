# =============================================================================
# DOMAIN: domain/engine_resolver.py
# =============================================================================
# Strategy Pattern para selecionar o engine OCR correto baseado na classificação.
#
# Origem: extraído da função _resolve_engine() de agent/router.py (Fase 3).
# O router.py original não é modificado — mantém sua própria _resolve_engine()
# para backward compat. A partir da Fase 5, application/ passará a usar este módulo.
#
# Responsabilidade ÚNICA: receber doc_type + optional engine_override e retornar
# o nome do engine a utilizar. Sem chamadas de OCR, sem HTTP, sem extração de campos.
#
# Pattern: Strategy
#   EngineResolver é o "contexto" — ele delega a decisão para seu registro interno.
#   Adicionar um novo engine = registrar no ENGINE_DEFAULTS, sem tocar no código
#   que chama o resolver.
# =============================================================================

from __future__ import annotations

from typing import Optional


# Mapeamento padrão: doc_type classificado → engine OCR
ENGINE_DEFAULTS: dict[str, str] = {
    "digital_pdf": "docling",
    "scanned_image": "openrouter",
    "handwritten_complex": "openrouter",
}

# Aliases: nomes alternativos aceitos no parâmetro selected_engine da API
ENGINE_ALIASES: dict[str, str] = {
    "paddleocr": "paddle",
    "paddle_ocr": "paddle",
    "llama-parse": "llamaparse",
    "deepseek-ocr": "deepseek",
    "hybrid": "paddle_easyocr",
    "paddle_deepseek": "paddle_easyocr",
}

# Engines disponíveis por tipo — usado por GET /engines e para validação
CAPABILITIES: dict[str, list[str]] = {
    "digital_pdf": ["docling"],
    "scanned_image": ["openrouter", "tesseract"],
    "handwritten_complex": ["openrouter", "tesseract"],
}

# Engine de último recurso — quando classification não mapeia para nenhum padrão
DEFAULT_FALLBACK_ENGINE = "tesseract"


class EngineResolver:
    """
    Decide qual engine OCR usar baseado no tipo de documento classificado.

    Prioridade da decisão:
    1. selected_engine (override manual via API) — após normalizar aliases
    2. Engine padrão registrado para o doc_type (ENGINE_DEFAULTS)
    3. Fallback global (tesseract) se classification desconhecida

    Exemplo de uso:
        resolver = EngineResolver()
        engine = resolver.get_engine("scanned_image")         # → "paddle"
        engine = resolver.get_engine("digital_pdf", "trocr") # → "trocr" (override)
    """

    def __init__(
        self,
        defaults: dict[str, str] | None = None,
        aliases: dict[str, str] | None = None,
        fallback: str = DEFAULT_FALLBACK_ENGINE,
    ) -> None:
        # Permite injetar configurações customizadas (útil para testes).
        self._defaults = defaults if defaults is not None else ENGINE_DEFAULTS
        self._aliases = aliases if aliases is not None else ENGINE_ALIASES
        self._fallback = fallback

    def get_engine(self, classification: str, selected_engine: str | None = None) -> str:
        """
        Retorna o nome do engine a usar para o documento.

        Args:
            classification:  Resultado de domain/classifier.classify_document()
            selected_engine: Override opcional vindo da API (pode ser None)

        Returns:
            Nome do engine (string), nunca None.
        """
        # Override manual: normaliza aliases e aceita se válido.
        if selected_engine:
            normalized = selected_engine.lower().strip()
            normalized = self._aliases.get(normalized, normalized)
            if normalized not in {"", "none", "null"}:
                return normalized

        # Padrão por tipo de documento.
        return self._defaults.get(classification, self._fallback)

    def get_capabilities(self, classification: str) -> list[str]:
        """Retorna lista de engines compatíveis com o tipo de documento."""
        return list(CAPABILITIES.get(classification, []))

    def list_all_engines(self) -> list[str]:
        """Retorna todos os engines únicos registrados em CAPABILITIES."""
        seen: set[str] = set()
        result: list[str] = []
        for engines in CAPABILITIES.values():
            for engine in engines:
                if engine not in seen:
                    seen.add(engine)
                    result.append(engine)
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Instância padrão — pronta para uso sem precisar instanciar manualmente.
# application/process_document.py (Fase 5) usará esta instância.
# ─────────────────────────────────────────────────────────────────────────────
resolver = EngineResolver()


def resolve_engine(classification: str, selected_engine: str | None = None) -> str:
    """Função de conveniência: delega para o resolver padrão."""
    return resolver.get_engine(classification, selected_engine)
