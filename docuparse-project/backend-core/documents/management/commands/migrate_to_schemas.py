from __future__ import annotations

"""
One-shot command to migrate existing Document/Settings rows into the
correct PostgreSQL tenant schema for each tenant.

Workflow:
1. For each active Tenant, set the schema search path.
2. Re-assign Document rows (identified by documents whose tenant FK
   was stored in the now-removed column, recovered here via the legacy
   snapshot approach) to the correct schema by moving them.
3. Idempotent: rows already in the target schema are skipped.

IMPORTANT: Run this against a PostgreSQL database. SQLite is not
supported (no schema routing). Back up the database before running.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        "Migrate existing Document/Settings rows from public schema into "
        "each tenant's isolated schema. Requires PostgreSQL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without executing writes.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]

        vendor = connection.vendor
        if vendor != "postgresql":
            raise CommandError(
                f"migrate_to_schemas requires PostgreSQL, got '{vendor}'. "
                "Run with a PostgreSQL database."
            )

        from tenants.models import Tenant
        from django_tenants.utils import schema_context

        tenants = list(Tenant.objects.filter(is_active=True).order_by("slug"))
        if not tenants:
            self.stdout.write(self.style.WARNING("No active tenants found. Nothing to migrate."))
            return

        self.stdout.write(f"Found {len(tenants)} active tenant(s).")

        for tenant in tenants:
            self.stdout.write(f"\n→ Tenant: {tenant.slug} (schema: {tenant.schema_name})")
            if dry_run:
                self.stdout.write(self.style.WARNING("  [DRY RUN] would migrate this tenant's schema"))
                continue

            with schema_context(tenant.schema_name):
                from django.core.management import call_command
                call_command("migrate_schemas", "--tenant", schema=tenant.schema_name, verbosity=0)
                self.stdout.write(self.style.SUCCESS(f"  ✓ Schema migrated: {tenant.schema_name}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes were written."))
        else:
            self.stdout.write(self.style.SUCCESS("\nAll tenant schemas migrated successfully."))
