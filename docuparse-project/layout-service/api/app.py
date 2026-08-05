from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from application.layout_event_worker import start_worker_thread_from_env
from docuparse_observability.tracing import configure_tracing
from docuparse_storage import get_storage
from domain.classifier import classify_layout
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from api.schemas import ClassifyLayoutRequest, ClassifyLayoutResponse

logger = logging.getLogger(__name__)

configure_tracing("layout-service")
RedisInstrumentor().instrument()


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
FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas.

    Nenhuma chamada manual a `span.record_exception()` é necessária aqui
    (US4): `FastAPIInstrumentor` já insere um middleware dedicado
    (`ExceptionHandlerMiddleware`) que grava o evento de exceção e marca
    `status=ERROR` no span ativo antes de qualquer exception_handler rodar
    — mesmo quando, como aqui, a exceção é capturada e convertida numa
    resposta 500 em vez de propagar. Confirmado empiricamente (T059).
    """
    logger.error(f"Exceção não tratada: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docuparse-layout-service"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "docuparse-layout-service"}


@app.post("/api/v1/classify-layout", response_model=ClassifyLayoutResponse)
async def classify_layout_endpoint(
    request: ClassifyLayoutRequest,
) -> ClassifyLayoutResponse:
    classification = classify_layout(_resolve_raw_text(request), request.document_type)
    return ClassifyLayoutResponse(
        layout=classification.layout,
        confidence=classification.confidence,
        document_type=request.document_type,
        requires_human_validation=classification.requires_human_validation,
        metadata=request.metadata,
    )
