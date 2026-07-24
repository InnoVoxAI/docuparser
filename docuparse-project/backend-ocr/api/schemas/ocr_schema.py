# =============================================================================
# API: api/schemas/ocr_schema.py
# =============================================================================
# Modelos Pydantic para entrada e saída da API OCR.
#
# Origem: extraído de main.py (Fase 6 do refactor).
# O main.py original permanece intacto para backward compat.
#
# O que há aqui:
#   - OCRResponse     → estrutura completa do response do endpoint /process
#   - Transcription   → modelo interno (pode ser usado por outros endpoints)
#   - EngineInfo      → resposta do endpoint GET /engines
#   - ProcessRequest  → entrada do endpoint POST /process (se necessário)
#
# Regra: zero lógica de negócio — só validação e serialização de dados.
# =============================================================================

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class Transcription(BaseModel):
    """
    Modelo interno para dados de transcrição OCR.
    Usado internamente e pode ser exposto por outros endpoints.
    """

    fields: dict[str, str] = Field(..., description="Campos extraídos do documento")
    required_fields: list[str] = Field(..., description="Lista de campos obrigatórios")
    field_validation: dict[str, Any] = Field(
        ..., description="Resultado da validação por campo"
    )
    field_confidence: dict[str, Any] | None = Field(
        None, description="Confiança por campo"
    )
    critical_field_scores: dict[str, float] | None = Field(
        None, description="Scores dos campos críticos"
    )
    low_confidence_fields: list[str] | None = Field(
        None, description="Campos com baixa confiança"
    )
    low_confidence_critical_fields: dict[str, str] | None = Field(
        None, description="Campos críticos com baixa confiança"
    )
    low_confidence_threshold: float | None = Field(
        None, description="Threshold de baixa confiança"
    )


class OCRResponse(BaseModel):
    """
    Resposta completa do endpoint POST /process.

    Contém todos os dados extraídos do documento OCR processado.
    """

    # Dados extraídos
    fields: dict[str, Any] = Field(..., description="Campos estruturados extraídos")
    field_positions: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Posições dos campos no texto"
    )

    # Metadados de qualidade
    final_score: float = Field(
        ..., description="Score final de qualidade da extração", ge=0.0, le=1.0
    )
    field_confidence: dict[str, Any] = Field(
        default_factory=dict, description="Confiança detalhada por campo"
    )
    low_confidence_fields: list[str] = Field(
        default_factory=list, description="Campos com baixa confiança"
    )

    # Dados brutos do OCR
    raw_text: str = Field("", description="Texto bruto extraído pelo OCR")
    raw_text_fallback: str = Field("", description="Texto de fallback se disponível")
    raw_text_formatted: str = Field(
        "",
        description="Texto com layout espacial preservado (colunas, tabelas); disponível apenas para DoclingEngine",
    )

    # Metadados do processamento
    document_type: str = Field(..., description="Tipo de documento classificado")
    engine_used: str = Field(..., description="Engine OCR utilizado")
    preprocessing_hint: str = Field(
        "", description="Hint de pre-processamento escolhido para o engine OCR"
    )
    classification_engine_preprocessing_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Mapa CLASSIFICATION_ENGINE_PREPROCESSING_HINTS para a classificacao do documento",
    )
    processing_time_seconds: float = Field(
        ..., description="Tempo total de processamento", gt=0
    )
    filename: str = Field(..., description="Nome do arquivo original")
    semantic_extraction_enabled: bool = Field(
        False, description="Indica se a extração estruturada legada foi executada"
    )

    # Dados estruturados adicionais
    document_info: dict[str, Any] = Field(
        default_factory=dict, description="Informações do documento"
    )
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Entidades detectadas"
    )
    tables: list[dict[str, Any]] = Field(
        default_factory=list, description="Tabelas detectadas"
    )
    totals: dict[str, Any] = Field(
        default_factory=dict, description="Totais monetários detectados"
    )

    # Debug info (opcional, só em modo debug)
    debug: dict[str, Any] | None = Field(None, description="Informações de debug")


class EngineInfo(BaseModel):
    """
    Informações sobre um engine OCR disponível.
    Resposta do endpoint GET /engines.
    """

    name: str = Field(..., description="Nome do engine")
    description: str = Field(..., description="Descrição do engine")
    supported_document_types: list[str] = Field(
        ..., description="Tipos de documento suportados"
    )
    is_default_for: list[str] = Field(
        default_factory=list, description="Tipos onde é engine padrão"
    )
    capabilities: list[str] = Field(
        default_factory=list, description="Capacidades especiais"
    )
    available: bool = Field(True, description="Engine registrado no runtime atual")
    is_configured: bool = Field(
        True, description="Dependências e credenciais mínimas configuradas"
    )
    status: str = Field("available", description="Status operacional resumido")


class ProcessRequest(BaseModel):
    """
    Entrada opcional do endpoint POST /process.
    Permite override de parâmetros via query/body.
    """

    selected_engine: str | None = Field(None, description="Engine OCR a utilizar")
    timeout_seconds: int | None = Field(120, description="Timeout em segundos", gt=0)
    extract_positions: bool | None = Field(
        True, description="Extrair posições dos campos"
    )
    legacy_extraction: bool | None = Field(
        False, description="Executar extração estruturada legada no backend OCR"
    )


class EnginesListResponse(BaseModel):
    """
    Resposta do endpoint GET /engines.
    Lista todos os engines disponíveis com suas capacidades.
    """

    engines: list[EngineInfo] = Field(..., description="Lista de engines disponíveis")
    total_count: int = Field(..., description="Número total de engines")
