from __future__ import annotations

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import connection
from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_tenant_domain_model

from tenants.models import Tenant


class JWTTenantMiddleware(TenantMainMiddleware):
    """Resolves the active PostgreSQL schema from the JWT 'tenant' claim.

    For requests authenticated with the static internal service token, falls
    back to the X-Tenant HTTP header.  Inactive tenants raise 403 immediately.
    """

    HEADER_NAME = "HTTP_X_TENANT"

    # Routes served straight out of the public schema (see core/urls.py's
    # public_urlpatterns): login/register can't require a JWT tenant claim
    # before a JWT exists, and tenant provisioning is itself public-schema
    # administration, not a per-tenant operation.
    PUBLIC_PATH_PREFIXES = ("/admin/", "/api/auth/", "/api/admin/tenants/")

    # Exact-path exemptions: liveness probes that must work with no auth at
    # all (e.g. the Docker healthcheck). Not a prefix — most of /api/ocr/ is
    # genuinely tenant-scoped and must keep requiring tenant resolution.
    PUBLIC_EXACT_PATHS = ("/api/ocr/health",)

    def process_request(self, request: object) -> None:
        # The base TenantMainMiddleware resolves tenants from the request's
        # hostname and calls get_tenant(domain_model, hostname) with no
        # `request` arg, so it's overridden wholesale here — tenant
        # resolution is JWT/header-based, not hostname-based.
        connection.set_schema_to_public()

        if request.path.startswith(self.PUBLIC_PATH_PREFIXES) or request.path in self.PUBLIC_EXACT_PATHS:
            request.tenant = None
            return

        domain_model = get_tenant_domain_model()
        tenant = self.get_tenant(domain_model, None, request)
        request.tenant = tenant
        # No resolvable tenant (no credentials, or credentials that don't
        # name one) isn't necessarily fatal here: some endpoints have no
        # per-tenant data and gate access themselves (e.g. _internal_token_error
        # in documents/views.py), so leave the connection on the public schema
        # and let DRF authentication/permissions or the view's own gate decide.
        # Credentials that DO name a tenant but it's missing/inactive still
        # raise below, in get_tenant — that's an actionable, specific error.
        if tenant is not None:
            connection.set_tenant(tenant)
            self.setup_url_routing(request)

    def get_tenant(self, model: type, hostname: str | None, request: object) -> Tenant | None:
        slug = self._resolve_slug(request)
        if slug is None:
            return None
        try:
            tenant = Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist:
            raise SuspiciousOperation(f"No tenant found for slug '{slug}'.")
        if not tenant.is_active:
            raise PermissionDenied(f"Tenant '{slug}' is inactive.")
        return tenant

    def _resolve_slug(self, request: object) -> str | None:
        auth_header: str = getattr(request, "META", {}).get("HTTP_AUTHORIZATION", "")
        internal_token = getattr(settings, "DOCUPARSE_INTERNAL_SERVICE_TOKEN", "").strip()

        if (
            internal_token
            and auth_header.startswith("Bearer ")
            and auth_header[len("Bearer "):] == internal_token
        ):
            slug = getattr(request, "META", {}).get(self.HEADER_NAME, "").strip()
            if not slug:
                raise SuspiciousOperation(
                    "X-Tenant header is required for internal service token requests."
                )
            return slug

        # JWT path: decode claims without full validation to extract tenant
        if auth_header.startswith("Bearer "):
            token_str = auth_header[len("Bearer "):]
            slug = self._slug_from_jwt(token_str)
            if slug:
                return slug

        # No Authorization header at all, or one that doesn't name a tenant
        # (e.g. not a Bearer token, or a JWT without a 'tenant' claim): not
        # fatal on its own, see the comment in process_request.
        return None

    @staticmethod
    def _slug_from_jwt(token_str: str) -> str | None:
        """Extracts the 'tenant' claim from a JWT without verifying the signature."""
        import base64
        import json

        parts = token_str.split(".")
        if len(parts) != 3:
            return None
        try:
            payload_b64 = parts[1]
            # Add padding if needed
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("tenant") or None
        except Exception:
            return None
