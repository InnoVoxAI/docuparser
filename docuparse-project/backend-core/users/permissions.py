from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
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


class HasAnyDocuparsePermission(BasePermission):
    """Allows the request when the caller holds *any* of `required_permissions`."""

    required_permissions: tuple[str, ...] = ()

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.auth == "service_token":
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        profile = getattr(request.user, "docuparse_profile", None)
        if not profile or not profile.role_ref:
            return False

        return profile.role_ref.permissions.filter(
            code__in=self.required_permissions
        ).exists()


def require_any_permission(*codes: str) -> type[BasePermission]:
    """Factory returning a DRF permission class that passes if the caller has
    at least one of the given permission codes."""
    suffix = "_or_".join(code.replace(".", "_") for code in codes)
    return type(
        f"HasAny_{suffix}",
        (HasAnyDocuparsePermission,),
        {"required_permissions": tuple(codes)},
    )


def require_permission_by_method(read: str, write: str) -> type[BasePermission]:
    """Factory: safe methods (GET/HEAD/OPTIONS) need `read`, the rest need `write`."""
    read_permission = require_permission(read)
    write_permission = require_permission(write)

    def has_permission(self: BasePermission, request: Request, view: Any) -> bool:
        permission = (
            read_permission if request.method in SAFE_METHODS else write_permission
        )
        return permission().has_permission(request, view)

    return type(
        f"Has_{read.replace('.', '_')}_write_{write.replace('.', '_')}",
        (BasePermission,),
        {"has_permission": has_permission},
    )
