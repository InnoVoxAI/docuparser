# =============================================================================
# DOMAIN: domain/field_extractor.py
# =============================================================================
# Interface de domínio para extração e scoring de campos estruturados (NFS-e).
#
# Origem: encapsula funções de utils/validate_fields.py (Fase 3 do refactor).
# A lógica concreta permanece em utils/validate_fields.py para backward compat.
# Na Fase 7, o código será migrado para cá e utils/validate_fields.py virará shim.
#
# Responsabilidade ÚNICA: extrair campos críticos do texto bruto OCR e calcular
# o score de confiança por campo. Não faz OCR, não faz HTTP, não sabe de engines.
#
# Campos críticos (NFS-e):
#   fornecedor, tomador, cnpj_fornecedor, numero_nf,
#   descricao_servico, valor_nf, retencao
# =============================================================================

from __future__ import annotations

from typing import Any

# Importa funções existentes como implementação concreta desta camada.
# Esta é a interface de domínio — o chamador (application/) sempre usa FieldExtractor,
# nunca importa diretamente de utils/.
from shared.validators import (
    REQUIRED_FIELDS,
    FIELD_CONFIDENCE_THRESHOLDS,
    LOW_CONFIDENCE_THRESHOLD,
    _get_raw_text,
    _is_header_like_value,
)

# A implementação agora mora em domain/field_extractor_impl.py.
# O shim utils/validate_fields.py ainda existe para compatibilidade externa.
from domain.field_extractor_impl import (
    compute_field_pipeline_quality,
    extract_fields_candidates,
    extract_dynamic_document_fields,
    extract_avg_confidence,
    merge_field_confidence,
    merge_fields_by_validation,
    resolve_field_fallback_engine,
    should_run_llm,
    extract_critical_fields_with_confidence,
    validate_fields,
    get_low_confidence_critical_fields,
)


class FieldExtractor:
    """
    Extrai e valida campos estruturados do texto bruto retornado por um engine OCR.

    Uso esperado em application/process_document.py (Fase 5):

        extractor = FieldExtractor()
        quality   = extractor.extract(ocr_data)
        fields    = quality["fields"]
        score     = quality["final_score"]

    Todos os métodos delegam para utils/validate_fields.py.
    Quando a migração completa ocorrer (Fase 7), a implementação será internalizada.
    """

    def extract(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Pipeline completo: extrai campos do OCR data e calcula scoring.

        Args:
            data: dict retornado por um engine OCR.
                  Deve conter 'raw_text' ou 'raw_text_fallback'.

        Returns:
            dict com:
              - fields:                    {campo: valor_extraído}
              - field_confidence:          {campo: score 0.0–1.0}
              - validation:                {campo: bool}
              - final_score:               float (0.0–1.0)
              - fallback_needed:           bool
              - low_confidence_fields:     list[str]
        """
        return compute_field_pipeline_quality(data)

    def extract_candidates(self, raw_text: str) -> dict[str, list[str]]:
        """
        Retorna múltiplos candidatos por campo antes da seleção final.
        Útil para debug e para o payload de candidatos exposto na API.
        """
        return extract_fields_candidates(raw_text)

    def extract_dynamic(
        self,
        data: dict[str, Any],
        base_fields: dict[str, Any],
        classification: str,
        engine_name: str,
    ) -> dict[str, str]:
        """
        Extrai campos adicionais além dos críticos via label-value pairs no texto.
        Retorna dict normalizado {chave_snake_case: valor}.
        """
        return extract_dynamic_document_fields(
            data=data,
            base_fields=base_fields,
            classification=classification,
            engine_name=engine_name,
        )

    def should_run_llm(self, low_conf_fields: dict[str, Any]) -> bool:
        """
        Decide se verificação semântica via LLM deve ser acionada.
        Verdadeiro quando campos críticos têm score abaixo do threshold (0.75).
        """
        return should_run_llm(low_conf_fields)

    def get_avg_confidence(self, data: dict[str, Any]) -> float | None:
        """Extrai confiança média do OCR a partir do dict retornado pelo engine."""
        return extract_avg_confidence(data)

    def merge_confidence(
        self,
        primary_confidence: dict[str, float],
        fallback_confidence: dict[str, float],
        fields_from_fallback: list[str],
    ) -> dict[str, float]:
        """Combina scores de confiança do engine primário e fallback."""
        return merge_field_confidence(
            primary_confidence=primary_confidence,
            fallback_confidence=fallback_confidence,
            fields_from_fallback=fields_from_fallback,
        )

    def merge_fields(
        self,
        primary_fields: dict[str, Any],
        fallback_fields: dict[str, Any],
        fallback_validation: dict[str, bool],
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Combina campos do engine primário com fallback, priorizando o melhor por campo.
        Retorna (merged_fields, lista_de_campos_que_vieram_do_fallback).
        """
        return merge_fields_by_validation(
            primary_fields=primary_fields,
            fallback_fields=fallback_fields,
            fallback_validation=fallback_validation,
        )

    def get_fallback_engine(self, classification: str, current_engine: str) -> str | None:
        """Retorna o engine de fallback recomendado para o doc_type e engine atual."""
        return resolve_field_fallback_engine(classification, current_engine)

    @property
    def required_fields(self) -> list[str]:
        """Lista dos campos críticos obrigatórios (NFS-e)."""
        return list(REQUIRED_FIELDS)


# ─────────────────────────────────────────────────────────────────────────────
# Instância padrão — pronta para uso sem precisar instanciar manualmente.
# application/process_document.py (Fase 5) usará esta instância.
# ─────────────────────────────────────────────────────────────────────────────
field_extractor = FieldExtractor()
