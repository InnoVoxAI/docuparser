import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounting", "0008_supplier_rule_chart_from_account")]

    operations = [
        migrations.AlterField(
            model_name="supplierrule",
            name="chart",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="supplier_rules",
                to="accounting.chartofaccounts",
            ),
        ),
        migrations.AddConstraint(
            model_name="supplierrule",
            constraint=models.UniqueConstraint(
                condition=models.Q(("condominium__isnull", False)),
                fields=("condominium", "supplier_tax_id", "keyword"),
                name="unique_supplier_rule_per_condominium",
            ),
        ),
        migrations.AddConstraint(
            model_name="supplierrule",
            constraint=models.UniqueConstraint(
                condition=models.Q(("condominium__isnull", True)),
                fields=("chart", "supplier_tax_id", "keyword"),
                name="unique_supplier_rule_per_chart",
            ),
        ),
    ]
