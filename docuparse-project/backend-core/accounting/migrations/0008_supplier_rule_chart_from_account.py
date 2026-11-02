from django.db import migrations


def chart_from_account(apps, schema_editor):
    """Regras existentes seguem valendo só para o condomínio; o plano é o da conta."""
    SupplierRule = apps.get_model("accounting", "SupplierRule")
    for rule in SupplierRule.objects.select_related("ledger_account"):
        SupplierRule.objects.filter(pk=rule.pk).update(
            chart_id=rule.ledger_account.chart_id
        )


class Migration(migrations.Migration):
    dependencies = [("accounting", "0007_supplier_rule_chart_scope")]

    operations = [migrations.RunPython(chart_from_account, migrations.RunPython.noop)]
