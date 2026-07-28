"""
Integration tests for the tenant provisioning API.

Tests marked `tenant_db` require POSTGRES_HOST env var (PostgreSQL with
schema routing). Tests without that marker run on any database.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from users.models import Permission, Role

from tenants.models import Tenant, UserProfile

User = get_user_model()


def _admin_client() -> tuple[APIClient, Tenant, User]:
    """Create an admin user with tenants.manage permission and return (client, tenant, user)."""
    client = APIClient()
    with patch.object(Tenant, "auto_create_schema", new=False):
        tenant = Tenant.objects.create(
            slug="admin-tenant", name="Admin Tenant", schema_name="tenant_admin_tenant"
        )
    perm, _ = Permission.objects.get_or_create(
        code="tenants.manage", defaults={"description": "Gerenciar Tenants"}
    )
    role = Role.objects.create(name="superadmin")
    role.permissions.add(perm)
    user = User.objects.create_user(
        username="super@admin.com",
        email="super@admin.com",
        password="pw",
        is_active=True,
    )
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)
    client.force_authenticate(user=user)
    return client, tenant, user


class TenantListCreateTests(TestCase):
    def setUp(self) -> None:
        self.client, self.tenant, self.user = _admin_client()

    def test_list_tenants_returns_active_tenants(self) -> None:
        response = self.client.get("/api/admin/tenants/")
        assert response.status_code == 200
        data = response.json()
        assert any(t["slug"] == "admin-tenant" for t in data["data"])

    def test_create_tenant_returns_201_with_slug(self) -> None:
        with patch.object(Tenant, "auto_create_schema", new=False):
            response = self.client.post(
                "/api/admin/tenants/",
                {"slug": "new-corp", "name": "New Corp"},
                format="json",
            )
        assert response.status_code == 201
        body = response.json()
        assert body["data"]["slug"] == "new-corp"
        assert Tenant.objects.filter(slug="new-corp").exists()

    def test_create_tenant_with_invalid_slug_returns_400(self) -> None:
        response = self.client.post(
            "/api/admin/tenants/",
            {"slug": "Invalid Slug!", "name": "Bad"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_tenant_with_duplicate_slug_returns_409(self) -> None:
        response = self.client.post(
            "/api/admin/tenants/",
            {"slug": "admin-tenant", "name": "Duplicate"},
            format="json",
        )
        assert response.status_code == 409

    def test_unauthenticated_request_returns_401(self) -> None:
        unauthenticated = APIClient()
        response = unauthenticated.get("/api/admin/tenants/")
        assert response.status_code == 401

    def test_user_without_tenants_manage_permission_returns_403(self) -> None:
        with patch.object(Tenant, "auto_create_schema", new=False):
            t = Tenant.objects.create(
                slug="other", name="Other", schema_name="tenant_other"
            )
        role = Role.objects.create(name="ordinary")
        u = User.objects.create_user(
            username="ord@t.com", email="ord@t.com", password="pw", is_active=True
        )
        UserProfile.objects.create(user=u, tenant=t, role_ref=role)
        client = APIClient()
        client.force_authenticate(user=u)
        response = client.get("/api/admin/tenants/")
        assert response.status_code == 403


class TenantDetailUpdateTests(TestCase):
    def setUp(self) -> None:
        self.client, self.tenant, self.user = _admin_client()

    def test_get_tenant_detail_returns_200(self) -> None:
        response = self.client.get(f"/api/admin/tenants/{self.tenant.slug}/")
        assert response.status_code == 200
        assert response.json()["data"]["slug"] == self.tenant.slug

    def test_patch_tenant_name_returns_200(self) -> None:
        response = self.client.patch(
            f"/api/admin/tenants/{self.tenant.slug}/",
            {"name": "Renamed Tenant"},
            format="json",
        )
        assert response.status_code == 200
        self.tenant.refresh_from_db()
        assert self.tenant.name == "Renamed Tenant"

    def test_deactivate_last_tenant_returns_409(self) -> None:
        response = self.client.patch(
            f"/api/admin/tenants/{self.tenant.slug}/",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == 409

    def test_get_nonexistent_tenant_returns_404(self) -> None:
        response = self.client.get("/api/admin/tenants/does-not-exist/")
        assert response.status_code == 404


@pytest.mark.tenant_db
class TenantSchemaIsolationTests:
    """
    These tests verify PostgreSQL schema routing. Requires POSTGRES_HOST.
    Skipped automatically on SQLite (see conftest.py).
    """

    def test_tenant_schema_is_created_on_provision(self) -> None:
        from django.db import connection

        slug = "isolation-test"
        schema_name = f"tenant_{slug}"
        tenant = Tenant.objects.create(
            slug=slug, name="Isolation Test", schema_name=schema_name
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name],
            )
            row = cursor.fetchone()
        assert row is not None, f"Schema '{schema_name}' was not created"
        tenant.delete()

    def test_documents_in_tenant_a_are_not_visible_in_tenant_b(self) -> None:
        from django_tenants.utils import schema_context
        from documents.models import Document

        slug_a, slug_b = "tenant-a-iso", "tenant-b-iso"
        tenant_a = Tenant.objects.create(
            slug=slug_a, name="A", schema_name=f"tenant_{slug_a}"
        )
        tenant_b = Tenant.objects.create(
            slug=slug_b, name="B", schema_name=f"tenant_{slug_b}"
        )

        with schema_context(tenant_a.schema_name):
            doc = Document.objects.create(
                status=Document.Status.RECEIVED,
                channel="manual",
                file_uri=f"local://{slug_a}/doc/original",
                original_filename="a.pdf",
                content_type="application/pdf",
                size_bytes=100,
            )
            doc_id = doc.id

        with schema_context(tenant_b.schema_name):
            assert not Document.objects.filter(id=doc_id).exists(), (
                f"Document from {slug_a} is visible in {slug_b}'s schema"
            )

        tenant_a.delete()
        tenant_b.delete()
