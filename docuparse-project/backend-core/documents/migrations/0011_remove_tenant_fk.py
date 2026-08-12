from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Remove tenant FK from all per-tenant models.
    Isolation is now enforced by PostgreSQL schema separation (django-tenants).
    """

    dependencies = [
        ("documents", "0010_backfill_field_versions"),
        # Must run after the legacy Tenant/UserProfile rows have been copied
        # into the tenants app models — this migration deletes those tables.
        ("tenants", "0003_migrate_legacy_tenant_data"),
    ]

    operations = [
        # Drop indexes that included tenant field
        migrations.RemoveIndex(
            model_name="document",
            name="documents_d_tenant__1461e3_idx",
        ),
        migrations.RemoveIndex(
            model_name="document",
            name="documents_d_tenant__35a2b9_idx",
        ),
        migrations.RemoveIndex(
            model_name="documentevent",
            name="documents_d_tenant__3a4754_idx",
        ),
        # Remove tenant FK from Document
        migrations.RemoveField(
            model_name="document",
            name="tenant",
        ),
        # Remove tenant FK from DocumentEvent
        migrations.RemoveField(
            model_name="documentevent",
            name="tenant",
        ),
        # Remove tenant OneToOneField from IntegrationSettings
        migrations.RemoveField(
            model_name="integrationsettings",
            name="tenant",
        ),
        # Remove tenant OneToOneField from OCRSettings
        migrations.RemoveField(
            model_name="ocrsettings",
            name="tenant",
        ),
        # Remove tenant OneToOneField from EmailSettings
        migrations.RemoveField(
            model_name="emailsettings",
            name="tenant",
        ),
        # Remove tenant FK from SchemaConfig + fix constraint
        migrations.RemoveConstraint(
            model_name="schemaconfig",
            name="unique_schema_config_version",
        ),
        migrations.RemoveField(
            model_name="schemaconfig",
            name="tenant",
        ),
        migrations.AddConstraint(
            model_name="schemaconfig",
            constraint=models.UniqueConstraint(
                fields=["schema_id", "version"],
                name="unique_schema_config_version",
            ),
        ),
        # Remove tenant FK from LayoutConfig + fix constraint
        migrations.RemoveConstraint(
            model_name="layoutconfig",
            name="unique_layout_config",
        ),
        migrations.RemoveField(
            model_name="layoutconfig",
            name="tenant",
        ),
        migrations.AddConstraint(
            model_name="layoutconfig",
            constraint=models.UniqueConstraint(
                fields=["layout", "document_type"],
                name="unique_layout_config",
            ),
        ),
        # Add new per-tenant indexes (without tenant field)
        migrations.AddIndex(
            model_name="document",
            index=models.Index(fields=["status"], name="documents_d_status_idx"),
        ),
        migrations.AddIndex(
            model_name="document",
            index=models.Index(
                fields=["received_at"], name="documents_d_received_at_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="documentevent",
            index=models.Index(
                fields=["event_type"], name="documents_d_event_type_idx"
            ),
        ),
        # Remove Tenant and UserProfile models from documents app
        # (they now live in tenants app)
        migrations.DeleteModel(
            name="UserProfile",
        ),
        migrations.DeleteModel(
            name="Tenant",
        ),
    ]
