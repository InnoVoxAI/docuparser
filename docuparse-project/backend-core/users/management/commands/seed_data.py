from __future__ import annotations

import os

from django.core.management.base import BaseCommand

from users.models import Permission, Role
from users.management.commands.seed_permissions import PERMISSIONS


class Command(BaseCommand):
    help = "Seed permissions, admin role, and admin user in the public schema (idempotent)"

    def handle(self, *args: object, **options: object) -> None:
        from tenants.models import Tenant, UserProfile
        from django.contrib.auth import get_user_model

        User = get_user_model()

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

        tenant = Tenant.objects.first()
        if tenant:
            profile, _ = UserProfile.objects.get_or_create(
                user=user, defaults={"tenant": tenant}
            )
            profile.role_ref = role
            profile.tenant = tenant
            profile.save()
            self.stdout.write("seed_data: admin profile ready")

            from documents.models import SchemaConfig
            import models.nota_fiscal.definition as _nf_def
            import models.contadeagua.definition as _agua_def

            DEFAULT_SCHEMAS = [
                {"schema_id": _nf_def.SCHEMA_ID, "version": _nf_def.VERSION, "definition": _nf_def.EXTRACTION_DEFINITION},
                {"schema_id": _agua_def.SCHEMA_ID, "version": _agua_def.VERSION, "definition": _agua_def.EXTRACTION_DEFINITION},
            ]

            for schema_spec in DEFAULT_SCHEMAS:
                _, created = SchemaConfig.objects.update_or_create(
                    schema_id=schema_spec["schema_id"],
                    version=schema_spec["version"],
                    defaults={"definition": schema_spec["definition"], "is_active": True},
                )
                verb = "created" if created else "updated"
                self.stdout.write(f"seed_data: {verb} schema {schema_spec['schema_id']}")

            from documents.models import LayoutConfig
            DEFAULT_LAYOUT_CONFIGS = [
                {"layout": "nota_fiscal", "schema_id": _nf_def.SCHEMA_ID},
                {"layout": "fatura_condominio", "schema_id": _agua_def.SCHEMA_ID},
                {"layout": "fatura_energia", "schema_id": _agua_def.SCHEMA_ID},
            ]
            for lc_spec in DEFAULT_LAYOUT_CONFIGS:
                schema = SchemaConfig.objects.filter(schema_id=lc_spec["schema_id"], is_active=True).first()
                if not schema:
                    continue
                _, created = LayoutConfig.objects.get_or_create(
                    layout=lc_spec["layout"],
                    document_type="",
                    defaults={"schema_config": schema, "is_active": True},
                )
                if created:
                    self.stdout.write(f"seed_data: created layout config {lc_spec['layout']}")
        else:
            self.stdout.write("seed_data: no tenant found — skipping per-tenant seeds (run after tenant provisioning)")
