from __future__ import annotations

import os

from django.core.management.base import BaseCommand

from users.models import Permission, Role
from users.management.commands.seed_permissions import PERMISSIONS


class Command(BaseCommand):
    help = "Seed permissions, admin role, admin user, and per-tenant defaults (idempotent)"

    def handle(self, *args: object, **options: object) -> None:
        from tenants.models import Tenant, UserProfile
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # ── Public schema: permissions, role, admin user ──────────────────────
        for code, description in PERMISSIONS:
            Permission.objects.get_or_create(code=code, defaults={"description": description})
        self.stdout.write("seed_data: permissions ready")

        role, _ = Role.objects.get_or_create(name="admin")
        role.permissions.set(Permission.objects.all())
        role.save()
        self.stdout.write("seed_data: admin role ready")

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@docuparse.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

        user, created = User.objects.get_or_create(
            username=admin_email,
            defaults={"email": admin_email, "is_active": True, "is_staff": True},
        )
        if created:
            user.set_password(admin_password)
            user.save()
            self.stdout.write(f"seed_data: created admin user {admin_email}")
        else:
            self.stdout.write(f"seed_data: admin user {admin_email} already exists")

        # ── Ensure default tenant exists ──────────────────────────────────────
        default_slug = os.environ.get("DEFAULT_TENANT_SLUG", "demo")
        default_name = os.environ.get("DEFAULT_TENANT_NAME", "Demo Company")
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
            self.stdout.write(f"seed_data: default tenant '{default_slug}' already exists")

        # ── Public schema: admin UserProfile linked to default tenant ─────────
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"tenant": tenant})
        profile.role_ref = role
        profile.tenant = tenant
        profile.save()
        self.stdout.write("seed_data: admin profile ready")

        # ── Per-tenant schema: SchemaConfig and LayoutConfig ──────────────────
        # SchemaConfig / LayoutConfig are tenant-app models — must use schema_context.
        from django_tenants.utils import schema_context
        from documents.models import SchemaConfig, LayoutConfig
        import models.nota_fiscal.definition as _nf_def
        import models.contadeagua.definition as _agua_def

        DEFAULT_SCHEMAS = [
            {"schema_id": _nf_def.SCHEMA_ID, "version": _nf_def.VERSION, "definition": _nf_def.EXTRACTION_DEFINITION},
            {"schema_id": _agua_def.SCHEMA_ID, "version": _agua_def.VERSION, "definition": _agua_def.EXTRACTION_DEFINITION},
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
                    self.stdout.write(f"seed_data [{t.slug}]: {'created' if c else 'updated'} schema {spec['schema_id']}")

                for lc_spec in DEFAULT_LAYOUT_CONFIGS:
                    schema = SchemaConfig.objects.filter(schema_id=lc_spec["schema_id"], is_active=True).first()
                    if not schema:
                        continue
                    _, c = LayoutConfig.objects.get_or_create(
                        layout=lc_spec["layout"],
                        document_type="",
                        defaults={"schema_config": schema, "is_active": True},
                    )
                    if c:
                        self.stdout.write(f"seed_data [{t.slug}]: created layout config {lc_spec['layout']}")
