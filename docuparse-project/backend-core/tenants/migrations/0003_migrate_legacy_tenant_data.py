from __future__ import annotations

from django.db import migrations

DEFAULT_TENANT_SLUG = "default"
DEFAULT_TENANT_SCHEMA = "tenant_default"


def migrate_legacy_tenant_data(apps, schema_editor):
    """Consolidate pre-multi-tenancy data into a single 'default' tenant.

    Deployments that predate this feature stored everything directly in the
    public schema under documents.Tenant / documents.UserProfile. Those models
    are dropped by documents/0011_remove_tenant_fk, so this migration must run
    first (see that migration's dependencies) to copy whatever exists there
    into the new tenants app models before it's gone for good.
    """
    # documents is a TENANT_APP, so its tables are never created in the public
    # schema this migration runs in — only real pre-multi-tenancy deployments
    # ever had documents_tenant/documents_userprofile here. Check via
    # introspection before querying, or a fresh install/test DB (where those
    # tables simply don't exist) crashes with a ProgrammingError instead of
    # taking the no-op path below.
    with schema_editor.connection.cursor() as cursor:
        existing_tables = set(
            schema_editor.connection.introspection.table_names(cursor)
        )
    if (
        "documents_tenant" not in existing_tables
        or "documents_userprofile" not in existing_tables
    ):
        return  # Fresh install, nothing to consolidate.

    LegacyTenant = apps.get_model("documents", "Tenant")
    LegacyUserProfile = apps.get_model("documents", "UserProfile")
    Tenant = apps.get_model("tenants", "Tenant")
    Domain = apps.get_model("tenants", "Domain")
    UserProfile = apps.get_model("tenants", "UserProfile")

    # This runs in the shared (public) phase, but documents is a TENANT app: on a
    # fresh install its tables never exist in public, so querying them would raise
    # ProgrammingError. Their absence is precisely the fresh-install case — nothing
    # to consolidate. (Legacy deployments predating the split still have these
    # tables in public and fall through to the copy logic below.)
    existing_tables = set(schema_editor.connection.introspection.table_names())
    if (
        LegacyTenant._meta.db_table not in existing_tables
        and LegacyUserProfile._meta.db_table not in existing_tables
    ):
        return

    if not LegacyTenant.objects.exists() and not LegacyUserProfile.objects.exists():
        return  # Legacy tables exist but are empty, nothing to consolidate.

    default_tenant, _ = Tenant.objects.get_or_create(
        slug=DEFAULT_TENANT_SLUG,
        defaults={
            "name": "Default Tenant",
            "schema_name": DEFAULT_TENANT_SCHEMA,
            "is_active": True,
        },
    )

    # apps.get_model() returns a bare historical model, so TenantMixin.save()
    # (which normally runs CREATE SCHEMA on insert) never fires here — create
    # the physical schema ourselves so later per-tenant migrations can run in it.
    schema_editor.execute(f'CREATE SCHEMA IF NOT EXISTS "{DEFAULT_TENANT_SCHEMA}"')

    Domain.objects.get_or_create(
        tenant=default_tenant,
        defaults={"domain": DEFAULT_TENANT_SLUG, "is_primary": True},
    )

    for legacy_profile in LegacyUserProfile.objects.all():
        UserProfile.objects.update_or_create(
            user_id=legacy_profile.user_id,
            defaults={
                "tenant": default_tenant,
                "role_ref_id": legacy_profile.role_ref_id,
            },
        )


def reverse_noop(apps, schema_editor):
    pass  # Data consolidation is non-destructive; nothing meaningful to reverse.


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0002_populate_schema_name_and_domain"),
        ("documents", "0010_backfill_field_versions"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_tenant_data, reverse_noop),
    ]
