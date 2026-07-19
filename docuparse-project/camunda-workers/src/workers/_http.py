"""Shared HTTP client factory for DocuParse service calls."""
import httpx
from config import settings


def _auth_headers(tenant_id: str = "") -> dict:
    headers = {}
    token = settings.docuparse_internal_service_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if tenant_id:
        headers["X-Tenant"] = tenant_id
    return headers


def core_client(tenant_id: str, timeout: float = 30.0) -> httpx.AsyncClient:
    """backend-core is multi-tenant (schema-per-tenant via django-tenants); its
    tenant-resolution middleware requires an X-Tenant header when authenticating
    with the internal service token (tenants/middleware.py::_resolve_slug) —
    tenant_id is therefore required here, not optional, so a missing value
    fails loudly at the call site rather than as a 400 deep in backend-core."""
    return httpx.AsyncClient(
        base_url=settings.backend_core_url,
        headers=_auth_headers(tenant_id),
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
