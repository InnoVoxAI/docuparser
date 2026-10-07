"""Base dos testes de API de condomínios e plano de contas."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import Tenant, UserProfile
from users.models import Permission, Role

User = get_user_model()

ROLE_PERMISSIONS = {
    "tenantAdmin": ["inbox.view", "models.edit"],
    "operator": ["inbox.view"],
    "reviewer": ["inbox.view", "documents.validate"],
}


class TenantAPITestCase(TestCase):
    """Tenant com um usuário por role; o cliente começa autenticado como tenantAdmin."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="condos", name="Administradora")
        connection.set_tenant(self.tenant)
        for code in {c for codes in ROLE_PERMISSIONS.values() for c in codes}:
            Permission.objects.get_or_create(code=code, defaults={"description": code})
        self.tokens = {
            role_name: self.token_for(self.tenant, role_name)
            for role_name in ROLE_PERMISSIONS
        }
        self.authenticate("tenantAdmin")

    def token_for(self, tenant: Tenant, role_name: str) -> str:
        role, _ = Role.objects.get_or_create(name=role_name)
        role.permissions.set(
            Permission.objects.filter(code__in=ROLE_PERMISSIONS[role_name])
        )
        user = User.objects.create_user(
            username=f"{role_name}@{tenant.slug}.test", password="pw"
        )
        UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)
        token = RefreshToken.for_user(user)
        token["tenant"] = tenant.slug
        return str(token.access_token)

    def authenticate(self, role_name: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens[role_name]}")
