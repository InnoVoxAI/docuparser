"""Contrato do catálogo global (spec 018): matriz de permissão + globalidade.

Leitura (GET): `models.edit` OU `tenants.manage`. Escrita (POST/PATCH/DELETE):
apenas `tenants.manage`. Token de serviço interno: sempre liberado.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import Tenant, UserProfile
from users.models import Permission, Role

from catalog.defaults import PROTECTED_SCHEMA_IDS
from catalog.models import LayoutConfig, SchemaConfig

User = get_user_model()

_ROLE_PERMS = {
    "tenantAdmin": ["inbox.view", "models.create", "models.edit"],
    "admin": ["models.edit", "tenants.manage"],
    "operator": ["inbox.view"],
}


def _jwt_for(user: User, tenant: Tenant) -> str:
    token = RefreshToken.for_user(user)
    token["tenant"] = tenant.slug
    return str(token.access_token)


class CatalogPermissionMatrixTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="cat-perm", name="Catalog Perm")
        connection.set_tenant(self.tenant)

        for code in {c for perms in _ROLE_PERMS.values() for c in perms}:
            Permission.objects.get_or_create(code=code, defaults={"description": code})

        self.tokens: dict[str, str] = {}
        for role_name, perms in _ROLE_PERMS.items():
            role = Role.objects.create(
                name=role_name, is_platform_role=role_name == "admin"
            )
            role.permissions.set(Permission.objects.filter(code__in=perms))
            user = User.objects.create_user(
                username=f"{role_name}@cat.test", password="pw"
            )
            UserProfile.objects.create(user=user, tenant=self.tenant, role_ref=role)
            self.tokens[role_name] = _jwt_for(user, self.tenant)

        # O catálogo canônico já está seedado (catalog/0002); criamos só o
        # schema customizado extra e reusamos o protegido do seed.
        self.schema = SchemaConfig.objects.create(
            schema_id="custom_schema", version="v1", definition={"fields": []}
        )
        self.protected = SchemaConfig.objects.get(schema_id=PROTECTED_SCHEMA_IDS[0])

    def _auth(self, role_name: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens[role_name]}")

    # ── leitura ──────────────────────────────────────────────────────────────
    def test_tenant_admin_can_read(self) -> None:
        self._auth("tenantAdmin")
        assert self.client.get(reverse("schema-configs")).status_code == 200
        assert self.client.get(reverse("layout-configs")).status_code == 200

    def test_operator_cannot_read(self) -> None:
        self._auth("operator")
        assert self.client.get(reverse("schema-configs")).status_code == 403

    # ── escrita: tenantAdmin (models.edit, sem tenants.manage) → 403 ─────────
    def test_tenant_admin_cannot_write(self) -> None:
        self._auth("tenantAdmin")
        post = self.client.post(
            reverse("schema-configs"),
            {"schema_id": "x", "version": "v1", "definition": {}},
            format="json",
        )
        assert post.status_code == 403
        patch = self.client.patch(
            reverse("schema-config-detail", args=[self.schema.id]),
            {"is_active": False},
            format="json",
        )
        assert patch.status_code == 403
        delete = self.client.delete(
            reverse("schema-config-detail", args=[self.schema.id])
        )
        assert delete.status_code == 403

    # ── escrita: admin (tenants.manage) → ok ────────────────────────────────
    def test_platform_admin_can_create_schema(self) -> None:
        self._auth("admin")
        post = self.client.post(
            reverse("schema-configs"),
            {"schema_id": "novo", "version": "v1", "definition": {"fields": ["a"]}},
            format="json",
        )
        assert post.status_code == 201
        assert SchemaConfig.objects.filter(schema_id="novo").exists()

    def test_platform_admin_can_create_layout(self) -> None:
        self._auth("admin")
        post = self.client.post(
            reverse("layout-configs"),
            {
                "layout": "novo_layout",
                "document_type": "scanned_image",
                "schema_config_id": str(self.schema.id),
            },
            format="json",
        )
        assert post.status_code == 201

    def test_delete_protected_schema_returns_403(self) -> None:
        self._auth("admin")
        r = self.client.delete(
            reverse("schema-config-detail", args=[self.protected.id])
        )
        assert r.status_code == 403

    def test_delete_schema_with_layout_returns_409(self) -> None:
        LayoutConfig.objects.create(
            layout="linked", document_type="", schema_config=self.schema
        )
        self._auth("admin")
        r = self.client.delete(reverse("schema-config-detail", args=[self.schema.id]))
        assert r.status_code == 409

    def test_service_token_can_write(self) -> None:
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN="svc-token"):
            r = self.client.post(
                reverse("schema-configs"),
                {"schema_id": "svc", "version": "v1", "definition": {}},
                format="json",
                HTTP_AUTHORIZATION="Bearer svc-token",
                HTTP_X_TENANT=self.tenant.slug,
            )
        assert r.status_code == 201


@pytest.mark.tenant_db
class CatalogGlobalityTests:
    """Um LayoutConfig criado em contexto do tenant A é visível no contexto do
    tenant B, imediatamente, sem replicação — a tabela vive em `public`.

    NOTA: mesma convenção (classe pytest simples + `tenant_db`) de
    `tenants/tests/test_isolation.py::TenantIsolationTests`.
    """

    def test_layout_visible_across_tenants(self) -> None:
        from django_tenants.utils import schema_context

        tenant_a = Tenant.objects.create(
            slug="glob-a", name="A", schema_name="tenant_glob_a"
        )
        tenant_b = Tenant.objects.create(
            slug="glob-b", name="B", schema_name="tenant_glob_b"
        )
        try:
            with schema_context(tenant_a.schema_name):
                schema = SchemaConfig.objects.create(
                    schema_id="cross_x", version="v1", definition={}
                )
                LayoutConfig.objects.create(
                    layout="cross_layout", document_type="", schema_config=schema
                )

            with schema_context(tenant_b.schema_name):
                assert LayoutConfig.objects.filter(layout="cross_layout").exists()
        finally:
            LayoutConfig.objects.filter(layout="cross_layout").delete()
            SchemaConfig.objects.filter(schema_id="cross_x").delete()
            tenant_a.delete()
            tenant_b.delete()
