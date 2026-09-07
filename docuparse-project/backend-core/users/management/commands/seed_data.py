from __future__ import annotations

import os
from typing import TypedDict

from django.core.management.base import BaseCommand, CommandError

from users.models import Permission, Role


class RoleSpec(TypedDict):
    name: str
    is_platform_role: bool
    permissions: list[str]


PERMISSIONS: list[tuple[str, str]] = [
    ("inbox.view", "Visualizar Inbox"),
    ("documents.send", "Enviar Documentos"),
    ("documents.validate", "Validar Documentos"),
    ("models.create", "Criar Modelos"),
    ("models.edit", "Editar Modelos"),
    ("operations.access", "Acessar Operações"),
    ("users.manage", "Gerenciar Usuários"),
    ("roles.manage", "Gerenciar Roles"),
    ("tenants.manage", "Gerenciar Tenants"),
]

ROLE_SPECS: list[RoleSpec] = [
    {
        "name": "admin",
        "is_platform_role": True,
        "permissions": [
            "inbox.view",
            "documents.send",
            "documents.validate",
            "models.create",
            "models.edit",
            "operations.access",
            "users.manage",
            "roles.manage",
            "tenants.manage",
        ],
    },
    {
        "name": "tenantAdmin",
        "is_platform_role": False,
        "permissions": [
            "inbox.view",
            "documents.send",
            "documents.validate",
            "models.create",
            "models.edit",
            "operations.access",
            "users.manage",
        ],
    },
    {
        "name": "operator",
        "is_platform_role": False,
        "permissions": [
            "inbox.view",
            "documents.send",
            "documents.validate",
            "operations.access",
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seed permissions, admin role, admin user, and per-tenant defaults (idempotent)"
    )

    def handle(self, *args: object, **options: object) -> None:
        from django.contrib.auth import get_user_model
        from tenants.models import Tenant, UserProfile

        User = get_user_model()

        if Tenant.objects.exists():
            self.stdout.write("seed_data: banco já inicializado, nada a fazer")
            return

        # ── Public schema: permissions, role, admin user ──────────────────────
        for code, description in PERMISSIONS:
            Permission.objects.get_or_create(
                code=code, defaults={"description": description}
            )
        self.stdout.write("seed_data: permissions ready")

        roles_by_name: dict[str, Role] = {}
        for spec in ROLE_SPECS:
            role, role_created = Role.objects.get_or_create(
                name=spec["name"],
                defaults={"is_platform_role": spec["is_platform_role"]},
            )
            if role_created or role.permissions.count() != len(spec["permissions"]):
                role.permissions.set(
                    Permission.objects.filter(code__in=spec["permissions"])
                )
            role.is_platform_role = spec["is_platform_role"]
            role.save()
            roles_by_name[spec["name"]] = role
            self.stdout.write(
                f"seed_data: {'created' if role_created else 'updated'} role {spec['name']}"
            )

        role = roles_by_name["admin"]

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@docuparse.com")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin_password:
            raise CommandError("ADMIN_PASSWORD must be set in the environment.")

        # ── Ensure default tenant exists ──────────────────────────────────────
        default_slug = os.environ.get("DEFAULT_TENANT_SLUG")
        default_name = os.environ.get("DEFAULT_TENANT_NAME")
        if not default_slug or not default_name:
            raise CommandError(
                "DEFAULT_TENANT_SLUG and DEFAULT_TENANT_NAME must be set in the environment."
            )
        tenant, tenant_created = Tenant.objects.get_or_create(
            slug=default_slug,
            defaults={
                "name": default_name,
                "schema_name": f"tenant_{default_slug}",
                "is_active": True,
            },
        )
        if tenant_created:
            self.stdout.write(f"seed_data: created default tenant '{default_slug}'")
        else:
            self.stdout.write(
                f"seed_data: default tenant '{default_slug}' already exists"
            )

        # ── Public schema: single admin user, for the default tenant only ─────
        # O guardrail acima garante que este bloco só roda quando o banco está
        # vazio, logo o default é sempre o único tenant existente — não há
        # mais necessidade de um loop multi-tenant nem de senha por tenant.
        user, user_created = User.objects.get_or_create(
            username=admin_email,
            defaults={
                "email": admin_email,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if user_created:
            user.set_password(admin_password)
            user.save()
            self.stdout.write(f"seed_data: created admin user {admin_email}")
        else:
            self.stdout.write(f"seed_data: admin user {admin_email} already exists")

        _, profile_created = UserProfile.objects.get_or_create(
            user=user, defaults={"tenant": tenant, "role_ref": role}
        )
        if profile_created:
            self.stdout.write("seed_data: admin profile created")
        else:
            self.stdout.write("seed_data: admin profile already exists")

        # ── Catálogo global de tipos de documento (schema `public`) ───────────
        # Não há mais laço por-tenant: o catálogo é único e global (spec 018).
        # `catalog/0002_seed_default_catalog` já popula em toda subida via
        # `migrate_schemas --shared`; esta chamada é defensiva para o caminho
        # `manage.py migrate` puro (sqlite/dev) e mantém o primeiro boot
        # auto-suficiente. Idempotente.
        from catalog.defaults import seed_default_catalog

        seed_default_catalog()
        self.stdout.write("seed_data: global document-type catalog ready")
