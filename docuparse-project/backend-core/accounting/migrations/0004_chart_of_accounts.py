import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0003_document_classification"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChartOfAccounts",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "external_source",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                (
                    "external_id",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="chartofaccounts",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_id", ""), _negated=True),
                fields=("external_source", "external_id"),
                name="unique_chart_of_accounts_external_id_per_source",
            ),
        ),
        migrations.AddField(
            model_name="ledgeraccount",
            name="chart",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="accounts",
                to="accounting.chartofaccounts",
            ),
        ),
    ]
