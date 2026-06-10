# =============================================================================
# API: api/routes/document.py
# =============================================================================
# Endpoints HTTP para processamento de documentos OCR.
#
# Origem: extraído de main.py (Fase 6 do refactor).
# O main.py original permanece intacto para backward compat.
#
# Endpoints:
#   - POST /process  → recebe arquivo, chama process_document(), devolve response
#   - GET  /engines  → lista engines disponíveis e suas capacidades
#
# Regra: zero lógica de negócio — só HTTP, validação de entrada, serialização.
# Toda a lógica vai para application/process_document.py.
# =============================================================================

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from api.schemas.ocr_schema import (
    OCRResponse,
    EngineInfo,
    EnginesListResponse,
    ProcessRequest,
)
from application.process_document import ENGINE_REGISTRY, process_document
from domain.engine_resolver import resolver as engine_resolver

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", response_model=OCRResponse)
async def process_document_endpoint(
    file: UploadFile = File(...),
    selected_engine: str | None = Form(None),
    timeout_seconds: int = Form(120),
    legacy_extraction: bool = Form(False),
) -> OCRResponse:
    """
    Processa um documento através do pipeline OCR completo.

    Recebe um arquivo (PDF ou imagem), classifica automaticamente o tipo,
    seleciona o engine OCR apropriado, extrai campos estruturados e
    retorna todos os dados processados.

    Args:
        file: Arquivo a ser processado (PDF ou imagem)
        selected_engine: Override opcional do engine OCR
        timeout_seconds: Timeout para engines externos

    Returns:
        OCRResponse com todos os dados extraídos e metadados
    """
    try:
        # Validar entrada
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nome do arquivo é obrigatório")

        # Ler bytes do arquivo
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        # Log do processamento
        logger.info(f"Recebido arquivo: {file.filename} ({len(file_bytes)} bytes)")

        # Chamar serviço de aplicação
        result = process_document(
            file_bytes=file_bytes,
            filename=file.filename,
            selected_engine=selected_engine,
            timeout_s=timeout_seconds,
            legacy_extraction=legacy_extraction,
        )

        # Retornar resposta estruturada
        return OCRResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/engines", response_model=EnginesListResponse)
async def list_engines_endpoint() -> EnginesListResponse:
    """
    Lista todos os engines OCR disponíveis e suas capacidades.

    Útil para interfaces que permitem seleção manual de engine
    ou para debugging de capacidades por tipo de documento.

    Returns:
        Lista de engines com metadados
    """
    try:
        engines_info = []

        operational_engines = set(engine_resolver.list_all_engines())

        # Mapeamento de engines para suas capacidades (simplificado)
        engine_descriptions = {
            "tesseract": "Engine tradicional, bom para texto claro",
            "docling": "Otimizado para PDFs digitais",
            "openrouter": "Acesso a múltiplos modelos via API",
        }

        # Construir lista somente com engines do perfil operacional atual.
        all_engines = sorted(engine for engine in ENGINE_REGISTRY if engine in operational_engines)
        for engine_name in all_engines:
            # Encontrar tipos de documento onde este engine é padrão
            default_for = []
            for doc_type in ["digital_pdf", "scanned_image", "handwritten_complex"]:
                if engine_resolver.get_engine(doc_type) == engine_name:
                    default_for.append(doc_type)

            # Capacidades do engine (baseado no tipo)
            capabilities = []
            if engine_name == "docling":
                capabilities.append("digital_pdf")
            if engine_name == "openrouter":
                capabilities.append("ai_powered")
                capabilities.append("scanned_image")
                capabilities.append("handwriting")
            if engine_name == "tesseract":
                capabilities.append("fallback")

            is_configured = True
            status = "available"
            if engine_name == "openrouter":
                missing = [
                    name
                    for name in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL")
                    if not os.getenv(name, "").strip()
                ]
                if missing:
                    is_configured = False
                    status = f"missing_config:{','.join(missing)}"

            engines_info.append(EngineInfo(
                name=engine_name,
                description=engine_descriptions.get(engine_name, f"Engine {engine_name}"),
                supported_document_types=["digital_pdf", "scanned_image", "handwritten_complex"],
                is_default_for=default_for,
                capabilities=capabilities,
                available=True,
                is_configured=is_configured,
                status=status,
            ))

        return EnginesListResponse(
            engines=engines_info,
            total_count=len(engines_info)
        )

    except Exception as e:
        logger.error(f"Erro ao listar engines: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
