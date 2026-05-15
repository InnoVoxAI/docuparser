from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.schemas import ExtractRequest, ExtractResponse
from application.extraction_event_worker import start_worker_thread_from_env
from domain.extractor import extract_fields
from domain.llm_extractor import extract_with_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = start_worker_thread_from_env()
    app.state.extraction_worker = worker
    try:
        yield
    finally:
        if worker:
            worker.stop()


app = FastAPI(
    title="DocuParse LangExtract Service",
    description="Extrai campos estruturados a partir de texto e layout classificados",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docuparse-langextract-service"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "docuparse-langextract-service"}


@app.post("/api/v1/extract", response_model=ExtractResponse)
async def extract_endpoint(request: ExtractRequest) -> ExtractResponse:
    # When a schema_definition is supplied use the LLM extractor; otherwise fall back to regex.
    if request.schema_definition:
        extracted = extract_with_llm(
            request.raw_text,
            request.schema_definition,
            tenant_id=str(request.metadata.get("tenant_id", "unknown")),
        )
    else:
        extracted = extract_fields(request.raw_text, request.layout, request.document_type)

    return ExtractResponse(
        schema_id=extracted.schema_id,
        schema_version=extracted.schema_version,
        fields=extracted.fields,
        confidence=extracted.confidence,
        requires_human_validation=extracted.requires_human_validation,
        metadata=request.metadata,
    )
