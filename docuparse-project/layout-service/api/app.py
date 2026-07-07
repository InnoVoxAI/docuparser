from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI

from docuparse_storage import get_storage

from api.schemas import ClassifyLayoutRequest, ClassifyLayoutResponse
from application.layout_event_worker import start_worker_thread_from_env
from domain.classifier import classify_layout


def _resolve_raw_text(request: ClassifyLayoutRequest) -> str:
    if request.raw_text:
        return request.raw_text
    if not request.raw_text_uri:
        return ""
    # Resolve pelo storage compartilhado (despacha por esquema local://|s3://).
    try:
        raw = get_storage().get_bytes(request.raw_text_uri)
    except FileNotFoundError:
        return ""
    data = json.loads(raw.decode("utf-8"))
    return data.get("raw_text") or data.get("text") or ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = start_worker_thread_from_env()
    app.state.layout_worker = worker
    try:
        yield
    finally:
        if worker:
            worker.stop()


app = FastAPI(
    title="DocuParse Layout Service",
    description="Classifica layouts a partir do texto bruto de OCR",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docuparse-layout-service"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "docuparse-layout-service"}


@app.post("/api/v1/classify-layout", response_model=ClassifyLayoutResponse)
async def classify_layout_endpoint(request: ClassifyLayoutRequest) -> ClassifyLayoutResponse:
    classification = classify_layout(_resolve_raw_text(request), request.document_type)
    return ClassifyLayoutResponse(
        layout=classification.layout,
        confidence=classification.confidence,
        document_type=request.document_type,
        requires_human_validation=classification.requires_human_validation,
        metadata=request.metadata,
    )
