from __future__ import annotations

from django.db import migrations


def backfill_initial_versions(apps, schema_editor):
    """Cria uma versão inicial ativa para cada ExtractionResult existente."""
    ExtractionResult = apps.get_model("documents", "ExtractionResult")
    ExtractionFieldVersion = apps.get_model("documents", "ExtractionFieldVersion")

    for result in ExtractionResult.objects.select_related("document").all():
        document = result.document
        if ExtractionFieldVersion.objects.filter(document=document).exists():
            continue
        ExtractionFieldVersion.objects.create(
            document=document,
            version_number=1,
            source_type="INITIAL_EXTRACTION",
            fields=result.fields or {},
            confidence=result.confidence or 0.0,
            previous_version=None,
            created_by=None,
            is_active=True,
        )


def remove_backfilled_versions(apps, schema_editor):
    ExtractionFieldVersion = apps.get_model("documents", "ExtractionFieldVersion")
    ExtractionFieldVersion.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0009_extractionfieldversion_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_initial_versions, remove_backfilled_versions),
    ]
