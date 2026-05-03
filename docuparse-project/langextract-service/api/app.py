from __future__ import annotations

from fastapi import FastAPI

from api.schemas import ExtractRequest, ExtractResponse
from domain.extractor import extract_fields


app = FastAPI(
    title="DocuParse LangExtract Service",
    description="Extrai campos estruturados a partir de texto e layout classificados",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docuparse-langextract-service"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "docuparse-langextract-service"}


@app.post("/api/v1/extract", response_model=ExtractResponse)
async def extract_endpoint(request: ExtractRequest) -> ExtractResponse:
    extracted = extract_fields(request.raw_text, request.layout, request.document_type)
    return ExtractResponse(
        schema_id=extracted.schema_id,
        schema_version=extracted.schema_version,
        fields=extracted.fields,
        confidence=extracted.confidence,
        requires_human_validation=extracted.requires_human_validation,
        metadata=request.metadata,
    )
