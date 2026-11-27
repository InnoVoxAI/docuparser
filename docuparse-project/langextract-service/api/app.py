from __future__ import annotations

import logging

from docuparse_observability.tracing import configure_tracing, is_telemetry_enabled
from domain.llm_extractor import extract_with_llm
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from starlette.concurrency import run_in_threadpool

from api.schemas import ExtractRequest, ExtractResponse

logger = logging.getLogger(__name__)

configure_tracing("langextract-service")
if is_telemetry_enabled():
    HTTPXClientInstrumentor().instrument()


app = FastAPI(
    title="DocuParse LangExtract Service",
    description="Extrai campos estruturados a partir de texto e layout classificados",
    version="0.1.0",
)
if is_telemetry_enabled():
    FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas.

    Nenhuma chamada manual a `span.record_exception()` é necessária aqui
    (US4): `FastAPIInstrumentor` já insere um middleware dedicado
    (`ExceptionHandlerMiddleware`) que grava o evento de exceção e marca
    `status=ERROR` no span ativo antes de qualquer exception_handler rodar
    — mesmo quando, como aqui, a exceção é capturada e convertida numa
    resposta 500 em vez de propagar. Confirmado empiricamente (T058).
    """
    logger.error(f"Exceção não tratada: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docuparse-langextract-service"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "docuparse-langextract-service"}


@app.post("/api/v1/extract", response_model=ExtractResponse)
async def extract_endpoint(request: ExtractRequest) -> ExtractResponse:
    # extract_with_llm faz chamadas HTTP bloqueantes ao LLM: roda no threadpool
    # para não parar o event loop (senão /health e /ready param de responder e a
    # liveness do k8s reinicia o pod no meio da extração).
    extracted = await run_in_threadpool(
        extract_with_llm,
        request.raw_text,
        request.schema_definition,
        tenant_id=str(request.metadata.get("tenant_id", "unknown")),
    )

    return ExtractResponse(
        schema_id=extracted.schema_id,
        schema_version=extracted.schema_version,
        fields=extracted.fields,
        confidence=extracted.confidence,
        requires_human_validation=extracted.requires_human_validation,
        metadata=request.metadata,
    )
