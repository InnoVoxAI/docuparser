"""Suite consolidada de RBAC (task 11): matriz operator/tenantAdmin/admin contra
os endpoints protegidos por `models.edit` e `operations.access`, mais os cenários
de escalonamento de privilégio (task 5) e o bypass por service token.

Os papéis usados aqui espelham exatamente `seed_data.ROLE_SPECS` para não
divergir da fonte de verdade dos nomes/permissões reais de produção.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from documents.models import SchemaConfig
from docuparse_events import EventMessage, LocalJsonlEventBus, publish_dead_letter
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import Tenant, UserProfile

from users.management.commands.seed_data import PERMISSIONS, ROLE_SPECS
from users.models import Permission, Role

User = get_user_model()

MODELS_EDIT_ENDPOINTS = [
    "schema-configs",
    "layout-configs",
    "integration-settings",
    "ocr-settings",
    "email-settings",
]


def _seed_roles() -> dict[str, Role]:
    for code, description in PERMISSIONS:
        Permission.objects.get_or_create(
            code=code, defaults={"description": description}
        )

    roles: dict[str, Role] = {}
    for spec in ROLE_SPECS:
        role, _ = Role.objects.get_or_create(
            name=spec["name"], defaults={"is_platform_role": spec["is_platform_role"]}
        )
        role.permissions.set(Permission.objects.filter(code__in=spec["permissions"]))
        roles[spec["name"]] = role
    return roles


def _jwt_for(user: User, tenant: Tenant) -> str:
    """Token real com o claim 'tenant' que JWTTenantMiddleware usa para rotear
    para a schema do tenant — force_authenticate() não passa por esse middleware."""
    token = RefreshToken.for_user(user)
    token["tenant"] = tenant.slug
    return str(token.access_token)


class ModelsEditEndpointsRBACTest(TestCase):
    """schema-configs/schema-config-detail/layout-configs/settings(*) exigem
    models.edit: operator não tem essa permissão em seed_data, tenantAdmin e
    admin têm."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            slug="rbac-models-edit", name="RBAC Models Edit"
        )
        connection.set_tenant(self.tenant)
        self.roles = _seed_roles()

        self.tokens: dict[str, str] = {}
        for role_name in ("operator", "tenantAdmin", "admin"):
            user = User.objects.create_user(
                username=f"{role_name}@rbac.test", password="pw"
            )
            UserProfile.objects.create(
                user=user, tenant=self.tenant, role_ref=self.roles[role_name]
            )
            self.tokens[role_name] = _jwt_for(user, self.tenant)

        self.schema_config = SchemaConfig.objects.create(
            schema_id="rbac-test",
            version="v1",
            definition={"fields": []},
            is_active=True,
        )

    def _get(self, role_name: str, url_name: str, *args: object):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens[role_name]}")
        return self.client.get(reverse(url_name, args=args))

    def test_operator_blocked_from_models_edit_endpoints(self) -> None:
        for url_name in MODELS_EDIT_ENDPOINTS:
            with self.subTest(endpoint=url_name):
                self.assertEqual(self._get("operator", url_name).status_code, 403)
        with self.subTest(endpoint="schema-config-detail"):
            r = self._get("operator", "schema-config-detail", self.schema_config.id)
            self.assertEqual(r.status_code, 403)

    def test_tenant_admin_allowed_on_models_edit_endpoints(self) -> None:
        for url_name in MODELS_EDIT_ENDPOINTS:
            with self.subTest(endpoint=url_name):
                self.assertEqual(self._get("tenantAdmin", url_name).status_code, 200)
        with self.subTest(endpoint="schema-config-detail"):
            r = self._get("tenantAdmin", "schema-config-detail", self.schema_config.id)
            self.assertEqual(r.status_code, 200)

    def test_admin_allowed_on_models_edit_endpoints(self) -> None:
        for url_name in MODELS_EDIT_ENDPOINTS:
            with self.subTest(endpoint=url_name):
                self.assertEqual(self._get("admin", url_name).status_code, 200)
        with self.subTest(endpoint="schema-config-detail"):
            r = self._get("admin", "schema-config-detail", self.schema_config.id)
            self.assertEqual(r.status_code, 200)


class OperationsAccessEndpointsRBACTest(TestCase):
    """dlq-summary/dlq-events/dlq-requeue exigem operations.access: os três
    papéis de seed_data (operator, tenantAdmin, admin) possuem essa permissão."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            slug="rbac-operations", name="RBAC Operations"
        )
        connection.set_tenant(self.tenant)
        self.roles = _seed_roles()

        self.tokens: dict[str, str] = {}
        for role_name in ("operator", "tenantAdmin", "admin"):
            user = User.objects.create_user(
                username=f"{role_name}@rbac-ops.test", password="pw"
            )
            UserProfile.objects.create(
                user=user, tenant=self.tenant, role_ref=self.roles[role_name]
            )
            self.tokens[role_name] = _jwt_for(user, self.tenant)

    def _auth(self, role_name: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens[role_name]}")

    def test_all_three_roles_can_read_dlq_summary_and_events(self) -> None:
        for role_name in ("operator", "tenantAdmin", "admin"):
            with self.subTest(role=role_name):
                self._auth(role_name)
                summary = self.client.get(reverse("dlq-summary"))
                events = self.client.get(
                    reverse("dlq-events"), {"stream": "ocr.completed.dlq"}
                )
                self.assertEqual(summary.status_code, 200)
                self.assertEqual(events.status_code, 200)

    def test_all_three_roles_can_dry_run_requeue(self) -> None:
        with (
            tempfile.TemporaryDirectory() as event_dir,
            patch.dict(os.environ, {"DOCUPARSE_EVENT_BUS": "local"}),
            self.settings(DOCUPARSE_LOCAL_EVENT_DIR=event_dir),
        ):
            bus = LocalJsonlEventBus(event_dir)
            publish_dead_letter(
                bus,
                stream="ocr.completed",
                entry=EventMessage(
                    id=1, payload={"event_type": "ocr.completed", "event_id": "event-1"}
                ),
                error=ValueError("invalid event"),
                source="layout-service",
            )

            for role_name in ("operator", "tenantAdmin", "admin"):
                with self.subTest(role=role_name):
                    self._auth(role_name)
                    dry_run = self.client.post(
                        reverse("dlq-requeue"),
                        {"stream": "ocr.completed.dlq", "id": "1", "execute": False},
                        format="json",
                    )
                    self.assertEqual(dry_run.status_code, 200)


class PrivilegeEscalationRBACTest(TestCase):
    """Núcleo do guard de escalonamento de privilégio (task 5): tenantAdmin não
    pode atribuir a role de plataforma (admin), mas admin pode."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="rbac-escalation", defaults={"name": "RBAC Escalation"}
        )
        self.roles = _seed_roles()

        def _make_and_login(role_name: str, email: str) -> tuple[User, str]:
            user = User.objects.create_user(
                username=email, email=email, password="pw", is_active=True
            )
            UserProfile.objects.create(
                user=user, tenant=self.tenant, role_ref=self.roles[role_name]
            )
            token = self.client.post(
                "/api/auth/login", {"email": email, "password": "pw"}, format="json"
            ).data["access"]
            return user, token

        self.tenant_admin_user, self.tenant_admin_token = _make_and_login(
            "tenantAdmin", "tadmin@rbac-escalation.test"
        )
        self.admin_user, self.admin_token = _make_and_login(
            "admin", "admin@rbac-escalation.test"
        )
        self.target_user, _ = _make_and_login("operator", "op@rbac-escalation.test")

    def test_tenant_admin_assigning_admin_role_returns_403(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tenant_admin_token}")
        r = self.client.patch(
            f"/api/ocr/users/{self.target_user.id}",
            {"role_id": str(self.roles["admin"].id)},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_tenant_admin_assigning_tenant_admin_role_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tenant_admin_token}")
        r = self.client.patch(
            f"/api/ocr/users/{self.target_user.id}",
            {"role_id": str(self.roles["tenantAdmin"].id)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_admin_assigning_admin_role_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.patch(
            f"/api/ocr/users/{self.target_user.id}",
            {"role_id": str(self.roles["admin"].id)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)


class ServiceTokenBypassRBACTest(TestCase):
    """O bypass `request.auth == "service_token"` deve continuar valendo
    independentemente de models.edit/operations.access, para chamadas
    serviço↔serviço (ex.: langextract) autenticadas com o token interno."""

    TOKEN = "rbac-internal-token"

    def setUp(self) -> None:
        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            slug="rbac-service-token", name="RBAC Service Token"
        )
        connection.set_tenant(self.tenant)

    def test_service_token_bypasses_models_edit_check(self) -> None:
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN=self.TOKEN):
            r = self.client.get(
                reverse("schema-configs"),
                HTTP_AUTHORIZATION=f"Bearer {self.TOKEN}",
                HTTP_X_TENANT=self.tenant.slug,
            )
        self.assertEqual(r.status_code, 200)

    def test_service_token_bypasses_operations_access_check(self) -> None:
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN=self.TOKEN):
            r = self.client.get(
                reverse("dlq-summary"),
                HTTP_AUTHORIZATION=f"Bearer {self.TOKEN}",
                HTTP_X_TENANT=self.tenant.slug,
            )
        self.assertEqual(r.status_code, 200)
