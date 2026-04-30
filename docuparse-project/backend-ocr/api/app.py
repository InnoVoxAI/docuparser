# =============================================================================
# API: api/app.py
# =============================================================================
# Configuração principal do FastAPI para o backend OCR.
#
# Origem: unifica main.py + configuração (Fase 6 do refactor).
# O main.py original permanece intacto para backward compat.
#
# O que há aqui:
#   - Configuração do FastAPI (app, middlewares, CORS)
#   - Registro de routers (api/routes/)
#   - Configurações globais (logging, exception handlers)
#
# Regra: zero lógica de negócio — só setup da aplicação web.
# =============================================================================

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.document import router as document_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação."""
    logger.info("Iniciando DocuParse OCR Backend...")
    yield
    logger.info("Finalizando DocuParse OCR Backend...")


# Criar aplicação FastAPI
app = FastAPI(
    title="DocuParse OCR Backend",
    description="API para processamento OCR de documentos usando múltiplos engines",
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(
    document_router,
    prefix="/api/v1",
    tags=["documents"]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "healthy", "service": "docuparse-ocr-backend"}


# Root endpoint
@app.get("/")
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "service": "DocuParse OCR Backend",
        "version": "1.0.0",
        "description": "API para processamento OCR de documentos",
        "endpoints": {
            "POST /api/v1/process": "Processar documento OCR",
            "GET /api/v1/engines": "Listar engines disponíveis",
            "GET /health": "Health check"
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para exceções não tratadas."""
    logger.error(f"Exceção não tratada: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred"
        }
    )


# Configurar modo debug se necessário
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )