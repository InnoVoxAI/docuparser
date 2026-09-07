from django.db import migrations


def seed(apps, schema_editor):
    from catalog.defaults import seed_default_catalog

    SchemaConfig = apps.get_model("catalog", "SchemaConfig")
    LayoutConfig = apps.get_model("catalog", "LayoutConfig")
    seed_default_catalog(
        schema_config_model=SchemaConfig, layout_config_model=LayoutConfig
    )


class Migration(migrations.Migration):
    """Popula o catálogo global (2 SchemaConfig + 3 LayoutConfig canônicos) a
    partir de `catalog.defaults`. Idempotente (FR-007, FR-009). Roda em `public`
    na fase `migrate_schemas --shared`."""

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
