from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class HasDocuparsePermission(BasePermission):
    required_permission: str = ""

    def has_permission(self, request: Request, view: Any) -> bool:
        # Service-to-service calls are always allowed
        if request.auth == "service_token":
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        profile = getattr(request.user, "docuparse_profile", None)
        if not profile or not profile.role_ref:
            return False

        return profile.role_ref.permissions.filter(
            code=self.required_permission
        ).exists()


def require_permission(code: str) -> type[BasePermission]:
    """Factory returning a DRF permission class for the given permission code."""
    return type(
        f"Has_{code.replace('.', '_')}",
        (HasDocuparsePermission,),
        {"required_permission": code},
    )
