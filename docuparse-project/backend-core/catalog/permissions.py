from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


class CatalogPermission(BasePermission):
    """Catálogo global (spec 018):

    - leitura (GET): `models.edit` OU `tenants.manage`;
    - escrita (POST/PATCH/DELETE): apenas `tenants.manage` (operador de
      plataforma) — o catálogo é compartilhado, alterá-lo afeta todos os tenants;
    - token de serviço interno: sempre liberado (pipeline de extração).
    """

    READ_PERMISSIONS = ("models.edit", "tenants.manage")
    WRITE_PERMISSIONS = ("tenants.manage",)

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.auth == "service_token":
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        profile = getattr(request.user, "docuparse_profile", None)
        if not profile or not profile.role_ref:
            return False

        codes = (
            self.READ_PERMISSIONS
            if request.method in SAFE_METHODS
            else self.WRITE_PERMISSIONS
        )
        return profile.role_ref.permissions.filter(code__in=codes).exists()
