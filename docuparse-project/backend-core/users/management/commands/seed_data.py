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

        # ── Public schema: admin user for EVERY active tenant ─────────────────
        # The default tenant uses ADMIN_EMAIL directly.  Every other tenant gets
        # a separate User whose email is  admin@<slug>.<domain>  (derived from
        # ADMIN_EMAIL's domain part).  All share ADMIN_PASSWORD.
        for t in Tenant.objects.filter(is_active=True):
            tenant_admin_email = (
                admin_email if t.slug == default_slug else f"admin@{t.slug}"
            )

            user, created = User.objects.get_or_create(
                username=tenant_admin_email,
                defaults={
                    "email": tenant_admin_email,
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": tenant_admin_email == admin_email,
                },
            )
            if created:
                user.set_password(admin_password)
                user.save()
                self.stdout.write(
                    f"seed_data [{t.slug}]: created admin user {tenant_admin_email}"
                )
            else:
                self.stdout.write(
                    f"seed_data [{t.slug}]: admin user {tenant_admin_email} already exists"
                )

            _, profile_created = UserProfile.objects.get_or_create(
                user=user, defaults={"tenant": t, "role_ref": role}
            )
            if profile_created:
                self.stdout.write(f"seed_data [{t.slug}]: admin profile created")
            else:
                self.stdout.write(f"seed_data [{t.slug}]: admin profile already exists")

        # ── Per-tenant schema: SchemaConfig and LayoutConfig ──────────────────
        # SchemaConfig / LayoutConfig are tenant-app models — must use schema_context.
        import models.contadeagua.definition as _agua_def
        import models.nota_fiscal.definition as _nf_def
        from django_tenants.utils import schema_context
        from documents.models import LayoutConfig, SchemaConfig

        DEFAULT_SCHEMAS = [
            {
                "schema_id": _nf_def.SCHEMA_ID,
                "version": _nf_def.VERSION,
                "definition": _nf_def.EXTRACTION_DEFINITION,
            },
            {
                "schema_id": _agua_def.SCHEMA_ID,
                "version": _agua_def.VERSION,
                "definition": _agua_def.EXTRACTION_DEFINITION,
            },
        ]
        DEFAULT_LAYOUT_CONFIGS = [
            {"layout": "nota_fiscal", "schema_id": _nf_def.SCHEMA_ID},
            {"layout": "fatura_condominio", "schema_id": _agua_def.SCHEMA_ID},
            {"layout": "fatura_energia", "schema_id": _agua_def.SCHEMA_ID},
        ]

        for t in Tenant.objects.filter(is_active=True):
            with schema_context(t.schema_name):
                for spec in DEFAULT_SCHEMAS:
                    _, c = SchemaConfig.objects.update_or_create(
                        schema_id=spec["schema_id"],
                        version=spec["version"],
                        defaults={"definition": spec["definition"], "is_active": True},
                    )
                    self.stdout.write(
                        f"seed_data [{t.slug}]: {'created' if c else 'updated'} schema {spec['schema_id']}"
                    )

                for lc_spec in DEFAULT_LAYOUT_CONFIGS:
                    schema = SchemaConfig.objects.filter(
                        schema_id=lc_spec["schema_id"], is_active=True
                    ).first()
                    if not schema:
                        continue
                    _, c = LayoutConfig.objects.get_or_create(
                        layout=lc_spec["layout"],
                        document_type="",
                        defaults={"schema_config": schema, "is_active": True},
                    )
                    if c:
                        self.stdout.write(
                            f"seed_data [{t.slug}]: created layout config {lc_spec['layout']}"
                        )
