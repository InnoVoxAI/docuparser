# =============================================================================
# APPLICATION: application/process_document.py
# =============================================================================
# Serviço principal de orquestração — o coração da aplicação.
#
# Origem: extraído da função route_and_process() de agent/router.py (Fase 5).
# O router.py original permanece intacto para backward compat.
#
# Responsabilidade ÚNICA: orquestrar o fluxo completo de processamento OCR.
# Recebe arquivo, classifica, resolve engine, processa OCR bruto e constrói response.
#
# Fluxo:
#   1. Classificar documento (domain/classifier.py)
#   2. Resolver engine correto (domain/engine_resolver.py)
#   3. Executar OCR (infrastructure/engines/)
#   4. Opcionalmente extrair campos no modo legado
#   5. Calcular posições dos campos no modo legado (se necessário)
#   6. Construir response final
#
# Pattern: Use Case / Application Service
#   Esta é a "porta" principal da aplicação — o ponto de entrada para o domínio.
# =============================================================================

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from domain.classifier import classify_document, get_engine_preprocessing_hints_for_class
from domain.engine_resolver import resolver as engine_resolver
from domain.field_extractor import FieldExtractor
from infrastructure.engines.base_engine import BaseOCREngine
from infrastructure.engines.deepseek_engine import DeepSeekEngine
from infrastructure.engines.docling_engine import DoclingEngine
from infrastructure.engines.easyocr_engine import EasyOCREngine
from infrastructure.engines.llamaparse_engine import LlamaParseEngine
from infrastructure.engines.openrouter_engine import OpenRouterOCREngine
from infrastructure.engines.paddle_engine import PaddleOCREngine
from infrastructure.engines.tesseract_engine import TesseractEngine
from infrastructure.engines.trocr_engine import TrOCREngine
from infrastructure.fallback.fallback_handler import merge_fallback_result, should_trigger_fallback
from shared.preprocessing import decode_image

logger = logging.getLogger(__name__)

# Registry de engines disponíveis — lazy loading para evitar falhas de import
ENGINE_REGISTRY: Dict[str, BaseOCREngine] = {}

def _register_engine(name: str, engine_class):
    """Registra um engine de forma lazy, tratando erros de dependências."""
    try:
        ENGINE_REGISTRY[name] = engine_class()
        logger.info(f"Engine '{name}' registrado com sucesso")
    except Exception as e:
        logger.warning(f"Engine '{name}' não pôde ser registrado: {e}")
        # Engine fica indisponível mas não quebra a aplicação

# Registrar engines disponíveis
_register_engine("deepseek", lambda: DeepSeekEngine())
_register_engine("docling", lambda: DoclingEngine())
_register_engine("easyocr", lambda: EasyOCREngine())
_register_engine("llamaparse", lambda: LlamaParseEngine())
_register_engine("openrouter", lambda: OpenRouterOCREngine())
_register_engine("paddle", lambda: PaddleOCREngine())
_register_engine("tesseract", lambda: TesseractEngine())
_register_engine("trocr", lambda: TrOCREngine())


def process_document(
    file_bytes: bytes,
    filename: str,
    selected_engine: str | None = None,
    timeout_s: int = 120,
    legacy_extraction: bool = False,
) -> Dict[str, Any]:
    """
    Serviço principal: processa um documento através do pipeline OCR completo.

    Args:
        file_bytes:      Bytes do arquivo (PDF ou imagem)
        filename:        Nome original do arquivo
        selected_engine: Override opcional do engine (None = automático)
        timeout_s:       Timeout para operações HTTP (engines externos)
        legacy_extraction: Mantém extração estruturada antiga quando explicitamente solicitada

    Returns:
        Dict estruturado com texto bruto de OCR e metadados
    """
    start_time = time.time()
    logger.info(f"Processando documento: {filename} ({len(file_bytes)} bytes)")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. CLASSIFICAR DOCUMENTO (Domain)
    # ──────────────────────────────────────────────────────────────────────────
    try:
        doc_type = classify_document(filename, file_bytes)
        logger.info(f"Documento classificado como: {doc_type}")
    except Exception as e:
        logger.error(f"Erro na classificação: {e}")
        doc_type = "scanned_image"  # fallback seguro

    # ──────────────────────────────────────────────────────────────────────────
    # 2. RESOLVER ENGINE (Domain)
    # ──────────────────────────────────────────────────────────────────────────
    try:
        engine_name = engine_resolver.get_engine(doc_type, selected_engine)
        engine = ENGINE_REGISTRY.get(engine_name)
        if not engine:
            raise ValueError(f"Engine '{engine_name}' não encontrado no registry")
        logger.info(f"Engine selecionado: {engine_name}")
    except Exception as e:
        logger.error(f"Erro na resolução de engine: {e}")
        engine = ENGINE_REGISTRY["tesseract"]  # fallback mais seguro
        engine_name = "tesseract"

    classification_engine_preprocessing_hints = get_engine_preprocessing_hints_for_class(doc_type)
    preprocessing_hint = classification_engine_preprocessing_hints.get(engine_name, "")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. EXECUTAR OCR (Infrastructure)
    # ──────────────────────────────────────────────────────────────────────────
    try:
        metadata = {
            "doc_type": doc_type,
            "filename": filename,
            "timeout_s": timeout_s,
        }
        ocr_result = engine.process(file_bytes, metadata)
        logger.info(f"OCR executado com sucesso pelo engine: {engine_name}")
    except Exception as e:
        logger.error(f"Erro no OCR com engine {engine_name}: {e}")
        # Tentar fallback se disponível. O resultado primário pode não existir
        # quando o engine falha antes de retornar qualquer payload.
        fallback_engine_name = "tesseract" if engine_name != "tesseract" else "easyocr"
        if fallback_engine_name in ENGINE_REGISTRY:
            try:
                logger.info(f"Tentando fallback com engine: {fallback_engine_name}")
                fallback_engine = ENGINE_REGISTRY[fallback_engine_name]
                fallback_result = fallback_engine.process(file_bytes, metadata)
                primary_result = {
                    "raw_text": "",
                    "_meta": {
                        "error": str(e),
                        "failed_engine": engine_name,
                    },
                }
                ocr_result = merge_fallback_result(
                    primary_result,
                    fallback_result,
                    engine_name,
                    fallback_engine_name,
                )
                engine_name = f"{engine_name}_with_{fallback_engine_name}_fallback"
            except Exception as fallback_e:
                logger.error(f"Fallback também falhou: {fallback_e}")
                raise e
        else:
            raise e

    # ──────────────────────────────────────────────────────────────────────────
    # 4. EXTRAIR CAMPOS ESTRUTURADOS (modo legado opcional)
    # ──────────────────────────────────────────────────────────────────────────
    field_quality: Dict[str, Any] = {
        "fields": {},
        "final_score": 0.0,
        "field_confidence": {},
        "low_confidence_fields": [],
        "_meta": {
            "semantic_extraction": "disabled",
            "reason": "handled_by_langextract_service",
        },
    }
    fields: Dict[str, Any] = {}
    final_score = 0.0
    if legacy_extraction:
        try:
            extractor = FieldExtractor()
            field_quality = extractor.extract(ocr_result)
            fields = field_quality["fields"]
            final_score = field_quality["final_score"]
            logger.info(f"Campos extraídos com score final: {final_score:.2f}")
        except Exception as e:
            logger.error(f"Erro na extração de campos: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # 5. CALCULAR POSIÇÕES DOS CAMPOS (se necessário)
    # ──────────────────────────────────────────────────────────────────────────
    field_positions = {}
    if fields and ocr_result.get("raw_text"):
        try:
            field_positions = _compute_field_positions(fields, ocr_result["raw_text"])
        except Exception as e:
            logger.warning(f"Erro ao calcular posições dos campos: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # 6. CONSTRUIR RESPONSE FINAL
    # ──────────────────────────────────────────────────────────────────────────
    processing_time = time.time() - start_time

    response = {
        # Dados extraídos
        "fields": fields,
        "field_positions": field_positions,

        # Metadados de qualidade
        "final_score": final_score,
        "field_confidence": field_quality.get("field_confidence", {}),
        "low_confidence_fields": field_quality.get("low_confidence_fields", []),

        # Dados brutos do OCR
        "raw_text": ocr_result.get("raw_text", ""),
        "raw_text_fallback": ocr_result.get("raw_text_fallback", ""),

        # Metadados do processamento
        "document_type": doc_type,
        "engine_used": engine_name,
        "preprocessing_hint": preprocessing_hint,
        "classification_engine_preprocessing_hints": classification_engine_preprocessing_hints,
        "processing_time_seconds": round(processing_time, 2),
        "filename": filename,
        "semantic_extraction_enabled": legacy_extraction,

        # Dados estruturados adicionais
        "document_info": ocr_result.get("document_info", {}),
        "entities": ocr_result.get("entities", {}),
        "tables": ocr_result.get("tables", []),
        "totals": ocr_result.get("totals", {}),

        # Debug info
        "debug": {
            "classification": doc_type,
            "engine_used": engine_name,
            "preprocessing_hint": preprocessing_hint,
            "classification_engine_preprocessing_hints": classification_engine_preprocessing_hints,
            "engine_meta": ocr_result.get("_meta", {}),
            "field_extraction_meta": field_quality.get("_meta", {}),
        }
    }

    logger.info(f"Processamento concluído em {processing_time:.2f}s")
    return response


def _compute_field_positions(fields: Dict[str, Any], raw_text: str) -> Dict[str, Dict[str, Any]]:
    """
    Calcula as posições aproximadas dos campos no texto extraído.

    Esta é uma implementação simplificada. Em produção, poderia usar:
    - Análise de layout do PDF
    - Posicionamento relativo das bounding boxes
    - Análise sintática do texto
    """
    positions = {}
    text_lower = raw_text.lower()

    for field_name, field_value in fields.items():
        if not isinstance(field_value, str):
            continue

        # Busca simples pela primeira ocorrência do valor do campo
        field_lower = str(field_value).lower()
        start_pos = text_lower.find(field_lower)

        if start_pos != -1:
            positions[field_name] = {
                "start_position": start_pos,
                "end_position": start_pos + len(field_value),
                "confidence": 0.8,  # confiança estimada
            }

    return positions
