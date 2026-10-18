from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("condominiums", "0004_external_source_backfill"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="condominium",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_id", ""), _negated=True),
                fields=("external_source", "external_id"),
                name="unique_condominium_external_id_per_source",
            ),
        ),
    ]
