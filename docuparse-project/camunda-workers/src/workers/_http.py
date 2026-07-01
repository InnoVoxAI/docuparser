"""Shared HTTP client factory for DocuParse service calls."""
import httpx
from config import settings


def _auth_headers() -> dict:
    token = settings.docuparse_internal_service_token
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def core_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.backend_core_url,
        headers=_auth_headers(),
        timeout=timeout,
    )


def ocr_client(timeout: float = 180.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.backend_ocr_url,
        headers=_auth_headers(),
        timeout=timeout,
    )


def layout_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.layout_service_url,
        headers=_auth_headers(),
        timeout=timeout,
    )


def langextract_client(timeout: float = 120.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.langextract_service_url,
        headers=_auth_headers(),
        timeout=timeout,
    )
