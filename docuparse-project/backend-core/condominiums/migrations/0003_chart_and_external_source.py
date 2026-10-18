import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0004_chart_of_accounts"),
        ("condominiums", "0002_condominium_aliases"),
    ]

    operations = [
        migrations.AddField(
            model_name="condominium",
            name="external_source",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="condominium",
            name="chart_of_accounts",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="condominiums",
                to="accounting.chartofaccounts",
            ),
        ),
    ]
