from django.db import migrations


class Migration(migrations.Migration):
    """Spec 018 — o catálogo de tipos de documento passou para o app `catalog`
    (SHARED_APPS), que detém agora os nomes canônicos de constraint
    `unique_schema_config_version` / `unique_layout_config`. Django proíbe nomes
    de constraint duplicados entre modelos, então as constraints são removidas
    das tabelas legadas por-tenant (que ainda coexistem até
    `0015_drop_catalog_models`). Não-destrutivo: dados preservados.
    """

    dependencies = [
        ("documents", "0013_alter_emailsettings_webhook_url_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="layoutconfig",
            name="unique_layout_config",
        ),
        migrations.RemoveConstraint(
            model_name="schemaconfig",
            name="unique_schema_config_version",
        ),
    ]
