from __future__ import annotations

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django_tenants.middleware.main import TenantMainMiddleware

from tenants.models import Tenant


class JWTTenantMiddleware(TenantMainMiddleware):
    """Resolves the active PostgreSQL schema from the JWT 'tenant' claim.

    For requests authenticated with the static internal service token, falls
    back to the X-Tenant HTTP header.  Inactive tenants raise 403 immediately.
    """

    HEADER_NAME = "HTTP_X_TENANT"

    def get_tenant(self, model: type, hostname: str, request: object) -> Tenant:
        slug = self._resolve_slug(request)
        try:
            tenant = Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist:
            raise SuspiciousOperation(f"No tenant found for slug '{slug}'.")
        if not tenant.is_active:
            raise PermissionDenied(f"Tenant '{slug}' is inactive.")
        return tenant

    def _resolve_slug(self, request: object) -> str:
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

        raise SuspiciousOperation("No tenant context: missing JWT tenant claim or X-Tenant header.")

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
