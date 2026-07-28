from __future__ import annotations

from django.db import migrations


def populate_schema_name_and_domain(apps: object, schema_editor: object) -> None:
    """Backfill schema_name for existing Tenant rows and create one Domain per tenant."""
    Tenant = apps.get_model("tenants", "Tenant")
    Domain = apps.get_model("tenants", "Domain")

    for tenant in Tenant.objects.all():
        if not tenant.schema_name:
            tenant.schema_name = f"tenant_{tenant.slug}"
            tenant.save(update_fields=["schema_name"])

        if not Domain.objects.filter(tenant=tenant).exists():
            Domain.objects.create(
                tenant=tenant,
                domain=tenant.slug,
                is_primary=True,
            )


def reverse_populate(apps: object, schema_editor: object) -> None:
    pass  # Reversing is a no-op; data is non-destructive


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_schema_name_and_domain, reverse_populate),
    ]
