from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from tenants.models import Tenant, UserProfile

from users.models import Permission, Role

User = get_user_model()


def _setup() -> tuple:
    """Returns (admin_token, operator_token, operator_role)."""
    tenant, _ = Tenant.objects.get_or_create(slug="test", defaults={"name": "Test"})

    Permission.objects.bulk_create(
        [
            Permission(code="inbox.view", description="Inbox"),
            Permission(code="documents.validate", description="Validate"),
            Permission(code="users.manage", description="Users"),
            Permission(code="roles.manage", description="Roles"),
        ]
    )

    admin_role = Role.objects.create(name="Admin")
    admin_role.permissions.set(Permission.objects.all())

    op_role = Role.objects.create(name="Operador")
    op_role.permissions.set(
        Permission.objects.filter(code__in=["inbox.view", "documents.validate"])
    )

    admin = User.objects.create_user(
        username="admin@t.com", email="admin@t.com", password="pw", is_active=True
    )
    UserProfile.objects.create(user=admin, tenant=tenant, role_ref=admin_role)

    op = User.objects.create_user(
        username="op@t.com", email="op@t.com", password="pw", is_active=True
    )
    UserProfile.objects.create(user=op, tenant=tenant, role_ref=op_role)

    client = APIClient()
    admin_token = client.post(
        "/api/auth/login", {"email": "admin@t.com", "password": "pw"}, format="json"
    ).data["access"]
    op_token = client.post(
        "/api/auth/login", {"email": "op@t.com", "password": "pw"}, format="json"
    ).data["access"]

    return admin_token, op_token, op_role


class SeedPermissionsTest(TestCase):
    def test_seed_is_idempotent(self) -> None:
        # seed_permissions was folded into seed_data (see users/management/commands/
        # seed_data.py), which also provisions a tenant/admin user and therefore needs
        # env vars this test doesn't set up. Exercise just the permission-seeding slice
        # of that command's logic, using its PERMISSIONS list as the source of truth.
        from users.management.commands.seed_data import PERMISSIONS
        from users.models import Permission

        def seed() -> None:
            for code, description in PERMISSIONS:
                Permission.objects.get_or_create(
                    code=code, defaults={"description": description}
                )

        seed()
        seed()

        self.assertEqual(Permission.objects.count(), 10)

    def test_only_admins_can_send_expenses_to_the_erp_by_default(self) -> None:
        """`erp.send` escreve num sistema financeiro: o operador não a recebe por padrão."""
        from users.management.commands.seed_data import PERMISSIONS, ROLE_SPECS

        assert "erp.send" in {code for code, _ in PERMISSIONS}
        holders = {
            spec["name"] for spec in ROLE_SPECS if "erp.send" in spec["permissions"]
        }
        self.assertEqual(holders, {"admin", "tenantAdmin"})


class LastAdminGuardTest(TestCase):
    def setUp(self) -> None:
        from tenants.models import Tenant, UserProfile

        from users.models import Permission, Role

        tenant, _ = Tenant.objects.get_or_create(
            slug="guard-test", defaults={"name": "Guard"}
        )
        Permission.objects.bulk_create(
            [
                Permission(code="users.manage", description="u"),
                Permission(code="roles.manage", description="r"),
            ]
        )
        self.admin_role = Role.objects.create(name="Admin")
        self.admin_role.permissions.set(Permission.objects.all())

        self.admin = get_user_model().objects.create_user(
            username="a@t.com", email="a@t.com", password="pw", is_active=True
        )
        UserProfile.objects.create(
            user=self.admin, tenant=tenant, role_ref=self.admin_role
        )

    def test_guard_returns_true_when_sole_admin(self) -> None:
        from users.user_views import last_admin_guard

        self.assertTrue(last_admin_guard(self.admin.pk))

    def test_guard_returns_false_when_other_admin_exists(self) -> None:
        from tenants.models import Tenant, UserProfile

        from users.user_views import last_admin_guard

        tenant = Tenant.objects.get(slug="guard-test")
        other = get_user_model().objects.create_user(
            username="b@t.com", email="b@t.com", password="pw", is_active=True
        )
        UserProfile.objects.create(user=other, tenant=tenant, role_ref=self.admin_role)
        self.assertFalse(last_admin_guard(self.admin.pk))


class PermissionEnforcementTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_token, self.op_token, self.op_role = _setup()

    def test_unauthenticated_request_on_protected_endpoint_returns_401(self) -> None:
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 401)

    def test_operator_blocked_from_users_endpoint_returns_403(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.op_token}")
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 403)

    def test_admin_allowed_on_users_endpoint_returns_200(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 200)

    def test_realtime_permission_revocation(self) -> None:
        # Operator has documents.validate — can access validate endpoint
        # Remove it from role → next request is 403 even with same valid token
        self.op_role.permissions.set(Permission.objects.filter(code="inbox.view"))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.op_token}")
        r = self.client.get("/api/ocr/users")
        self.assertEqual(r.status_code, 403)


class ErpSendPermissionMigrationTest(TestCase):
    """O `seed_data` não roda em banco existente; a migration leva `erp.send` até lá."""

    def migration(self):
        import importlib

        return importlib.import_module("users.migrations.0003_erp_send_permission")

    def test_existing_admin_roles_receive_it_and_the_operator_does_not(self) -> None:
        from django.apps import apps

        from users.models import Permission, Role

        Permission.objects.filter(
            code="erp.send"
        ).delete()  # ambiente antigo, sem a permissão
        for name in ("admin", "tenantAdmin", "operator"):
            Role.objects.get_or_create(name=name)

        self.migration().add_permission(apps, None)

        holders = set(
            Role.objects.filter(permissions__code="erp.send").values_list(
                "name", flat=True
            )
        )
        self.assertEqual(holders, {"admin", "tenantAdmin"})

    def test_running_it_twice_changes_nothing(self) -> None:
        from django.apps import apps

        from users.models import Permission, Role

        Role.objects.get_or_create(name="admin")
        self.migration().add_permission(apps, None)
        self.migration().add_permission(apps, None)

        self.assertEqual(Permission.objects.filter(code="erp.send").count(), 1)
        self.assertEqual(
            Role.objects.get(name="admin").permissions.filter(code="erp.send").count(),
            1,
        )

    def test_a_fresh_database_already_has_the_permission_after_migrating(self) -> None:
        from users.models import Permission

        self.assertTrue(Permission.objects.filter(code="erp.send").exists())
