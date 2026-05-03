from __future__ import annotations

from fastapi import FastAPI

from api.schemas import ClassifyLayoutRequest, ClassifyLayoutResponse
from domain.classifier import classify_layout


app = FastAPI(
    title="DocuParse Layout Service",
    description="Classifica layouts a partir do texto bruto de OCR",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docuparse-layout-service"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "docuparse-layout-service"}


@app.post("/api/v1/classify-layout", response_model=ClassifyLayoutResponse)
async def classify_layout_endpoint(request: ClassifyLayoutRequest) -> ClassifyLayoutResponse:
    classification = classify_layout(request.raw_text, request.document_type)
    return ClassifyLayoutResponse(
        layout=classification.layout,
        confidence=classification.confidence,
        document_type=request.document_type,
        requires_human_validation=classification.requires_human_validation,
        metadata=request.metadata,
    )
