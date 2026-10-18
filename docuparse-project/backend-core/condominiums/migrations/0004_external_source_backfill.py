from django.db import migrations


def mark_existing_as_superlogica(apps, schema_editor):
    """`external_id` já era documentado como o id no Superlógica."""
    Condominium = apps.get_model("condominiums", "Condominium")
    Condominium.objects.exclude(external_id="").update(external_source="superlogica")


class Migration(migrations.Migration):
    dependencies = [
        ("condominiums", "0003_chart_and_external_source"),
    ]

    operations = [
        migrations.RunPython(mark_existing_as_superlogica, migrations.RunPython.noop),
    ]
