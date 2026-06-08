from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from documents.models import Tenant, UserProfile
from users.models import Permission, Role

User = get_user_model()


def _make_tenant() -> Tenant:
    return Tenant.objects.get_or_create(slug="test", defaults={"name": "Test"})[0]


def _make_role(name: str = "Admin", codes: list[str] | None = None) -> Role:
    role = Role.objects.create(name=name)
    if codes:
        perms = Permission.objects.filter(code__in=codes)
        role.permissions.set(perms)
    return role


def _make_user(
    email: str,
    password: str,
    role: Role | None = None,
    is_active: bool = True,
) -> User:
    tenant = _make_tenant()
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=email.split("@")[0],
        is_active=is_active,
    )
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)
    return user


class LoginViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        Permission.objects.bulk_create([
            Permission(code="inbox.view", description="Visualizar Inbox"),
            Permission(code="documents.validate", description="Validar Documentos"),
        ])
        self.role = _make_role("Operador", ["inbox.view", "documents.validate"])
        self.user = _make_user("op@test.com", "senha123", role=self.role)

    def test_login_success_returns_tokens_and_permissions(self) -> None:
        r = self.client.post(
            "/api/auth/login",
            {"email": "op@test.com", "password": "senha123"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("user", data)
        self.assertIn("permissions", data["user"])
        self.assertIn("inbox.view", data["user"]["permissions"])

    def test_login_invalid_credentials_returns_401(self) -> None:
        r = self.client.post(
            "/api/auth/login",
            {"email": "op@test.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(r.status_code, 401)

    def test_login_inactive_account_returns_403(self) -> None:
        _make_user("inactive@test.com", "senha123", role=self.role, is_active=False)
        r = self.client.post(
            "/api/auth/login",
            {"email": "inactive@test.com", "password": "senha123"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)


class LogoutViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        Permission.objects.create(code="inbox.view", description="Visualizar Inbox")
        role = _make_role("Operador", ["inbox.view"])
        self.user = _make_user("op@test.com", "senha123", role=role)

    def _login(self) -> dict:
        r = self.client.post(
            "/api/auth/login",
            {"email": "op@test.com", "password": "senha123"},
            format="json",
        )
        return r.json()

    def test_logout_with_valid_refresh_returns_204(self) -> None:
        tokens = self._login()
        r = self.client.post(
            "/api/auth/logout",
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(r.status_code, 204)

    def test_refresh_after_logout_returns_401(self) -> None:
        tokens = self._login()
        self.client.post(
            "/api/auth/logout",
            {"refresh": tokens["refresh"]},
            format="json",
        )
        r = self.client.post(
            "/api/auth/refresh",
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(r.status_code, 401)


class MeViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        Permission.objects.create(code="inbox.view", description="Visualizar Inbox")
        role = _make_role("Operador", ["inbox.view"])
        self.user = _make_user("op@test.com", "senha123", role=role)

    def _get_access_token(self) -> str:
        r = self.client.post(
            "/api/auth/login",
            {"email": "op@test.com", "password": "senha123"},
            format="json",
        )
        return r.json()["access"]

    def test_me_with_valid_token_returns_200(self) -> None:
        token = self._get_access_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.get("/api/auth/me")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["email"], "op@test.com")
        self.assertIn("permissions", data)

    def test_me_without_token_returns_401(self) -> None:
        r = self.client.get("/api/auth/me")
        self.assertEqual(r.status_code, 401)
