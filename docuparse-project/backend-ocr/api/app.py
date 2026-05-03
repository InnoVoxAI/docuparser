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
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_project_env()

from api.routes.document import router as document_router
from application.ocr_event_worker import start_worker_thread_from_env
from domain.engine_resolver import ENGINE_DEFAULTS

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _csv_env(name: str, default: str) -> list[str]:
    values = [value.strip() for value in os.getenv(name, default).split(",")]
    return [value for value in values if value]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação."""
    logger.info("Iniciando DocuParse OCR Backend...")
    app.state.ocr_worker = start_worker_thread_from_env()
    yield
    if getattr(app.state, "ocr_worker", None) is not None:
        app.state.ocr_worker.stop()
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
    allow_origins=_csv_env("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
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


@app.get("/ready")
async def readiness_check():
    """Readiness check for configured OCR profile dependencies."""
    missing: list[str] = []
    if "openrouter" in set(ENGINE_DEFAULTS.values()):
        missing.extend(
            name
            for name in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL")
            if not os.getenv(name, "").strip()
        )

    if missing:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "docuparse-ocr-backend",
                "missing": missing,
            },
        )

    return {"status": "ready", "service": "docuparse-ocr-backend"}


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
            "GET /health": "Health check",
            "GET /ready": "Readiness check"
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
