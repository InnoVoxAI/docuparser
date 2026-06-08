from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class DocuparseAuthentication(JWTAuthentication):
    """Tries JWT first; falls back to the static internal service token."""

    def authenticate(self, request: Any) -> tuple[Any, Any] | None:
        # Try JWT first
        try:
            result = super().authenticate(request)
            if result is not None:
                return result
        except (InvalidToken, TokenError):
            pass

        # Fall back to static service token
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            internal_token = getattr(settings, "DOCUPARSE_INTERNAL_SERVICE_TOKEN", "").strip()
            if internal_token and token == internal_token:
                return (AnonymousUser(), "service_token")

        return None
