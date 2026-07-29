from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from tenants.models import Tenant, UserProfile

from users.models import Permission, Role

User = get_user_model()


def _make_tenant() -> Tenant:
    return Tenant.objects.get_or_create(slug="test", defaults={"name": "Test"})[0]


def _seed_permissions() -> None:
    codes = ["users.manage", "roles.manage", "inbox.view", "documents.validate"]
    for code in codes:
        Permission.objects.get_or_create(code=code, defaults={"description": code})


def _make_admin_role() -> Role:
    role = Role.objects.create(name="Admin")
    role.permissions.set(Permission.objects.all())
    return role


def _make_platform_admin_role() -> Role:
    role = Role.objects.create(name="admin", is_platform_role=True)
    role.permissions.set(Permission.objects.all())
    return role


def _make_op_role() -> Role:
    role = Role.objects.create(name="Operador")
    role.permissions.set(
        Permission.objects.filter(code__in=["inbox.view", "documents.validate"])
    )
    return role


def _login(client: APIClient, email: str, password: str) -> str:
    r = client.post(
        "/api/auth/login", {"email": email, "password": password}, format="json"
    )
    return r.data["access"]


class UserManagementTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _seed_permissions()
        self.tenant = _make_tenant()
        self.admin_role = _make_admin_role()
        self.op_role = _make_op_role()

        admin = User.objects.create_user(
            username="admin@t.com", email="admin@t.com", password="pw", is_active=True
        )
        UserProfile.objects.create(
            user=admin, tenant=self.tenant, role_ref=self.admin_role
        )
        self.admin_token = _login(self.client, "admin@t.com", "pw")

        op = User.objects.create_user(
            username="op@t.com", email="op@t.com", password="pw", is_active=True
        )
        UserProfile.objects.create(user=op, tenant=self.tenant, role_ref=self.op_role)
        self.op_token = _login(self.client, "op@t.com", "pw")

    def test_list_users_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.data, list)

    def test_create_user_returns_201(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.post(
            "/api/ocr/users",
            {
                "name": "Novo",
                "email": "novo@t.com",
                "password": "senha123",
                "role_id": str(self.op_role.id),
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["email"], "novo@t.com")
        self.assertTrue(r.data["is_active"])

    def test_create_user_duplicate_email_returns_400(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.post(
            "/api/ocr/users",
            {
                "name": "Op2",
                "email": "op@t.com",
                "password": "senha123",
                "role_id": str(self.op_role.id),
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_get_user_detail_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        user = User.objects.get(username="op@t.com")
        r = self.client.get(f"/api/ocr/users/{user.id}")
        self.assertEqual(r.status_code, 200)

    def test_deactivate_user_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        op = User.objects.get(username="op@t.com")
        r = self.client.patch(
            f"/api/ocr/users/{op.id}", {"is_active": False}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        op.refresh_from_db()
        self.assertFalse(op.is_active)

    def test_deactivate_last_admin_returns_409(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        admin = User.objects.get(username="admin@t.com")
        r = self.client.patch(
            f"/api/ocr/users/{admin.id}", {"is_active": False}, format="json"
        )
        self.assertEqual(r.status_code, 409)

    def test_non_admin_accessing_users_returns_403(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.op_token}")
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 403)


class PrivilegeEscalationTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _seed_permissions()
        self.tenant = _make_tenant()
        self.platform_admin_role = _make_platform_admin_role()
        self.tenant_admin_role = _make_admin_role()
        self.op_role = _make_op_role()

        platform_admin = User.objects.create_user(
            username="padmin@t.com",
            email="padmin@t.com",
            password="pw",
            is_active=True,
        )
        UserProfile.objects.create(
            user=platform_admin, tenant=self.tenant, role_ref=self.platform_admin_role
        )
        self.platform_admin_token = _login(self.client, "padmin@t.com", "pw")

        tenant_admin = User.objects.create_user(
            username="tadmin@t.com",
            email="tadmin@t.com",
            password="pw",
            is_active=True,
        )
        UserProfile.objects.create(
            user=tenant_admin, tenant=self.tenant, role_ref=self.tenant_admin_role
        )
        self.tenant_admin_token = _login(self.client, "tadmin@t.com", "pw")

        op = User.objects.create_user(
            username="op2@t.com", email="op2@t.com", password="pw", is_active=True
        )
        UserProfile.objects.create(user=op, tenant=self.tenant, role_ref=self.op_role)
        self.op_user = op

        self.tenant_admin_user = tenant_admin

    def test_tenant_admin_promoting_other_user_to_platform_role_returns_403(
        self,
    ) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tenant_admin_token}")
        r = self.client.patch(
            f"/api/ocr/users/{self.op_user.id}",
            {"role_id": str(self.platform_admin_role.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_tenant_admin_promoting_self_to_platform_role_returns_403(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tenant_admin_token}")
        r = self.client.patch(
            f"/api/ocr/users/{self.tenant_admin_user.id}",
            {"role_id": str(self.platform_admin_role.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_platform_admin_promoting_user_to_platform_role_returns_200(self) -> None:
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.platform_admin_token}"
        )
        r = self.client.patch(
            f"/api/ocr/users/{self.op_user.id}",
            {"role_id": str(self.platform_admin_role.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_tenant_admin_assigning_non_platform_role_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tenant_admin_token}")
        r = self.client.patch(
            f"/api/ocr/users/{self.op_user.id}",
            {"role_id": str(self.tenant_admin_role.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_list_users_role_includes_is_platform_role(self) -> None:
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.platform_admin_token}"
        )
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 200)
        by_email = {u["email"]: u["role"]["is_platform_role"] for u in r.data}
        self.assertTrue(by_email["padmin@t.com"])
        self.assertFalse(by_email["tadmin@t.com"])
        self.assertFalse(by_email["op2@t.com"])
