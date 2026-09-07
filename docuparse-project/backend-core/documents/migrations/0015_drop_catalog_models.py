"""Spec 018 — remove as tabelas legadas do catálogo por-tenant.

Roda uma vez por schema de tenant na fase `migrate_schemas` (tenant). Antes de
qualquer `DROP TABLE`, `assert_only_canonical_rows` verifica que aquele schema
só tem as linhas canônicas; se achar linha customizada, levanta `RuntimeError`
nomeando o schema e aborta a migração **daquele** schema (FR-010) — os schemas
já migrados não são afetados. O runbook (quickstart 018) manda rodar
`check_catalog_divergence` antes do deploy para detectar isso sem depender do
meio de um `migrate_schemas`.

Irreversível na prática (dados destruídos). Rollback = restore de backup.
"""

from __future__ import annotations

from django.db import migrations


def assert_only_canonical_rows(apps, schema_editor):
    from catalog.defaults import default_catalog_specs

    SchemaConfig = apps.get_model("documents", "SchemaConfig")
    LayoutConfig = apps.get_model("documents", "LayoutConfig")

    specs = default_catalog_specs()
    canonical_schemas = {(s["schema_id"], s["version"]) for s in specs["schemas"]}
    canonical_layouts = {(lc["layout"], lc["document_type"]) for lc in specs["layouts"]}
    schema_name = getattr(schema_editor.connection, "schema_name", "?")

    extra_schemas = [
        f"schema_id={sc.schema_id!r} version={sc.version!r}"
        for sc in SchemaConfig.objects.all()
        if (sc.schema_id, sc.version) not in canonical_schemas
    ]
    extra_layouts = [
        f"layout={lc.layout!r} document_type={lc.document_type!r}"
        for lc in LayoutConfig.objects.all()
        if (lc.layout, lc.document_type) not in canonical_layouts
    ]

    if extra_schemas or extra_layouts:
        raise RuntimeError(
            f"[{schema_name}] catálogo customizado detectado: "
            f"{extra_schemas + extra_layouts}. "
            "Resolva antes de migrar (ver quickstart 018)."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0014_drop_legacy_catalog_constraints"),
        ("catalog", "0002_seed_default_catalog"),
    ]

    operations = [
        migrations.RunPython(
            assert_only_canonical_rows, reverse_code=migrations.RunPython.noop
        ),
        migrations.DeleteModel(name="LayoutConfig"),
        migrations.DeleteModel(name="SchemaConfig"),
    ]
