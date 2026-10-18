import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0005_chart_per_condominium"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="ledgeraccount",
            name="unique_ledger_account_code_per_condominium",
        ),
        migrations.RemoveConstraint(
            model_name="ledgeraccount",
            name="unique_ledger_account_nature_per_condominium",
        ),
        migrations.RemoveField(model_name="ledgeraccount", name="condominium"),
        migrations.AlterField(
            model_name="ledgeraccount",
            name="chart",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="accounts",
                to="accounting.chartofaccounts",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgeraccount",
            constraint=models.UniqueConstraint(
                fields=("chart", "code"), name="unique_ledger_account_code_per_chart"
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgeraccount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("nature", ""), _negated=True),
                fields=("chart", "nature"),
                name="unique_ledger_account_nature_per_chart",
            ),
        ),
    ]
