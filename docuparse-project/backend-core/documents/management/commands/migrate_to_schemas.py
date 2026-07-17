from __future__ import annotations

"""
One-shot command to migrate existing Document/Settings rows into the
correct PostgreSQL tenant schema for each tenant.

Workflow:
1. For each active Tenant (or just the one named by --tenant-slug), create
   its schema and run its tenant migrations.
2. Copy every documents-app row from the legacy `public` schema into that
   tenant's own schema via raw SQL. Idempotent: rows already present in the
   target schema (matched by primary key) are skipped.

IMPORTANT: Run this against a PostgreSQL database. SQLite is not
supported (no schema routing). Back up the database before running.

This command is meant for the one-time cutover from a pre-multi-tenancy,
single-schema deployment. Running it without --tenant-slug copies the same
public-schema rows into *every* active tenant, which is almost never what
you want once more than one real tenant exists — pass --tenant-slug to scope
it to the single legacy/default tenant.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

# Documents-app tables copied from the legacy `public` schema into each
# tenant's own schema. Ordered so FK targets exist before the rows that
# reference them; documents_extractionfieldversion additionally needs its
# own rows ordered by version_number so its self-referential
# previous_version FK resolves correctly within a single INSERT.
_COPY_TABLES: list[tuple[str, str | None]] = [
    ("documents_document", None),
    ("documents_schemaconfig", None),
    ("documents_integrationsettings", None),
    ("documents_ocrsettings", None),
    ("documents_emailsettings", None),
    ("documents_documentevent", None),
    ("documents_extractionresult", None),
    ("documents_extractionfieldversion", "version_number ASC"),
    ("documents_validationdecision", None),
    ("documents_erpintegrationattempt", None),
    ("documents_layoutconfig", None),
]


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
        parser.add_argument(
            "--tenant-slug",
            default=None,
            help="Only migrate the tenant with this slug, instead of every active tenant.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        tenant_slug: str | None = options["tenant_slug"]

        vendor = connection.vendor
        if vendor != "postgresql":
            raise CommandError(
                f"migrate_to_schemas requires PostgreSQL, got '{vendor}'. "
                "Run with a PostgreSQL database."
            )

        from tenants.models import Tenant

        tenants_qs = Tenant.objects.filter(is_active=True).order_by("slug")
        if tenant_slug:
            tenants_qs = tenants_qs.filter(slug=tenant_slug)
        tenants = list(tenants_qs)

        if not tenants:
            self.stdout.write(self.style.WARNING("No matching active tenant(s) found. Nothing to migrate."))
            return

        if len(tenants) > 1:
            self.stdout.write(self.style.WARNING(
                f"Migrating {len(tenants)} tenants — each will receive a full copy of the "
                "legacy public-schema rows. Pass --tenant-slug to scope this to a single "
                "tenant if that isn't what you want."
            ))

        self.stdout.write(f"Found {len(tenants)} matching tenant(s).")

        for tenant in tenants:
            self.stdout.write(f"\n→ Tenant: {tenant.slug} (schema: {tenant.schema_name})")
            if dry_run:
                for table, _ in _COPY_TABLES:
                    count = self._count("public", table)
                    self.stdout.write(self.style.WARNING(f"  [DRY RUN] would copy {count} row(s) from public.{table}"))
                continue

            from django.core.management import call_command

            call_command("migrate_schemas", "--tenant", schema=tenant.schema_name, verbosity=0)

            with transaction.atomic():
                for table, order_by in _COPY_TABLES:
                    before = self._count(tenant.schema_name, table)
                    order_clause = f" ORDER BY {order_by}" if order_by else ""
                    # The legacy public-schema table may still carry columns (e.g. the old
                    # `tenant_id` FK) that the current per-tenant table no longer has, so
                    # copy by the tenant table's own column list rather than `SELECT *`.
                    columns = self._columns(tenant.schema_name, table)
                    column_list = ", ".join(f'"{c}"' for c in columns)
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f'INSERT INTO "{tenant.schema_name}"."{table}" ({column_list}) '
                            f'SELECT {column_list} FROM "public"."{table}"{order_clause} '
                            f"ON CONFLICT DO NOTHING"
                        )
                    after = self._count(tenant.schema_name, table)
                    self.stdout.write(f"  {table}: {before} -> {after} row(s)")

            self.stdout.write(self.style.SUCCESS(f"  ✓ Schema migrated: {tenant.schema_name}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes were written."))
        else:
            self.stdout.write(self.style.SUCCESS("\nAll tenant schemas migrated successfully."))

    @staticmethod
    def _count(schema: str, table: str) -> int:
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT count(*) FROM "{schema}"."{table}"')
            return cursor.fetchone()[0]

    @staticmethod
    def _columns(schema: str, table: str) -> list[str]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s "
                "ORDER BY ordinal_position",
                [schema, table],
            )
            return [row[0] for row in cursor.fetchall()]
