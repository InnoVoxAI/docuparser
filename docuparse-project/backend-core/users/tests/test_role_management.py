from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from documents.models import Tenant, UserProfile
from users.models import Permission, Role

User = get_user_model()


def _setup() -> tuple:
    tenant, _ = Tenant.objects.get_or_create(slug="test", defaults={"name": "Test"})
    Permission.objects.bulk_create([
        Permission(code="inbox.view", description="Inbox"),
        Permission(code="documents.validate", description="Validate"),
        Permission(code="users.manage", description="Users"),
        Permission(code="roles.manage", description="Roles"),
    ])
    admin_role = Role.objects.create(name="Admin")
    admin_role.permissions.set(Permission.objects.all())

    op_role = Role.objects.create(name="Operador")
    op_role.permissions.set(Permission.objects.filter(code__in=["inbox.view"]))

    admin = User.objects.create_user(username="admin@t.com", email="admin@t.com", password="pw", is_active=True)
    UserProfile.objects.create(user=admin, tenant=tenant, role_ref=admin_role)

    op = User.objects.create_user(username="op@t.com", email="op@t.com", password="pw", is_active=True)
    UserProfile.objects.create(user=op, tenant=tenant, role_ref=op_role)

    client = APIClient()
    admin_token = client.post("/api/auth/login", {"email": "admin@t.com", "password": "pw"}, format="json").data["access"]
    op_token = client.post("/api/auth/login", {"email": "op@t.com", "password": "pw"}, format="json").data["access"]
    return admin_token, op_token, op_role


class RoleManagementTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_token, self.op_token, self.op_role = _setup()

    def test_list_permissions_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.get("/api/ocr/permissions")
        self.assertEqual(r.status_code, 200)
        codes = [p["code"] for p in r.data]
        self.assertIn("inbox.view", codes)

    def test_list_roles_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.get("/api/ocr/roles")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.data, list)

    def test_create_role_with_valid_permissions_returns_201(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.post(
            "/api/ocr/roles",
            {"name": "Coordenador", "permission_codes": ["inbox.view", "documents.validate"]},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "Coordenador")

    def test_create_role_with_empty_permissions_returns_400(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.post(
            "/api/ocr/roles",
            {"name": "Vazia", "permission_codes": []},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_create_role_with_invalid_permission_code_returns_400(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.post(
            "/api/ocr/roles",
            {"name": "Invalida", "permission_codes": ["nonexistent.perm"]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_create_duplicate_role_name_returns_400(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.post(
            "/api/ocr/roles",
            {"name": "Admin", "permission_codes": ["inbox.view"]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_update_role_permissions_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.patch(
            f"/api/ocr/roles/{self.op_role.id}",
            {"permission_codes": ["inbox.view", "documents.validate"]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_delete_unused_role_returns_204(self) -> None:
        role = Role.objects.create(name="Temporaria")
        role.permissions.set(Permission.objects.filter(code="inbox.view"))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.delete(f"/api/ocr/roles/{role.id}")
        self.assertEqual(r.status_code, 204)

    def test_delete_role_in_use_returns_409(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.delete(f"/api/ocr/roles/{self.op_role.id}")
        self.assertEqual(r.status_code, 409)

    def test_non_admin_accessing_roles_returns_403(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.op_token}")
        r = self.client.get("/api/ocr/roles")
        self.assertEqual(r.status_code, 403)
