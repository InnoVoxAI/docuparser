import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0006_ledger_account_belongs_to_chart"),
        ("condominiums", "0005_external_source_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplierrule",
            name="chart",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="supplier_rules",
                to="accounting.chartofaccounts",
            ),
        ),
        migrations.AddField(
            model_name="supplierrule",
            name="origin",
            field=models.CharField(
                choices=[
                    ("manual", "Manual"),
                    ("history", "Histórico do ERP"),
                    ("learned", "Aprendida com o analista"),
                ],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="supplierrule",
            name="evidence_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="supplierrule",
            name="evidence_total",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="supplierrule",
            name="alternatives",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="supplierrule",
            name="condominium",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="supplier_rules",
                to="condominiums.condominium",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="supplierrule",
            name="unique_supplier_rule_per_condominium",
        ),
    ]
