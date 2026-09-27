from django.db import migrations


def seed(apps, schema_editor):
    from catalog.defaults import seed_default_catalog

    SchemaConfig = apps.get_model("catalog", "SchemaConfig")
    LayoutConfig = apps.get_model("catalog", "LayoutConfig")
    seed_default_catalog(
        schema_config_model=SchemaConfig, layout_config_model=LayoutConfig
    )


class Migration(migrations.Migration):
    """Reaplica o seed idempotente de `catalog.defaults` para incluir o schema
    `boleto_default` e seus 4 LayoutConfig em bases onde a 0002 já rodou."""

    dependencies = [
        ("catalog", "0002_seed_default_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
