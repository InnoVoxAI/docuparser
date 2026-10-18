from django.db import migrations


def charts_from_condominium_accounts(apps, schema_editor):
    """Cada condomínio com contas vira dono de um plano só dele (sem deduplicar)."""
    Condominium = apps.get_model("condominiums", "Condominium")
    LedgerAccount = apps.get_model("accounting", "LedgerAccount")
    ChartOfAccounts = apps.get_model("accounting", "ChartOfAccounts")

    for condominium in Condominium.objects.filter(
        ledger_accounts__isnull=False
    ).distinct():
        chart = ChartOfAccounts.objects.create(
            name=f"Plano de contas de {condominium.name}"[:255]
        )
        LedgerAccount.objects.filter(condominium=condominium).update(chart=chart)
        Condominium.objects.filter(pk=condominium.pk).update(chart_of_accounts=chart)


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0004_chart_of_accounts"),
        ("condominiums", "0003_chart_and_external_source"),
    ]

    operations = [
        # Sem volta: planos compartilhados não voltam a ser por condomínio.
        migrations.RunPython(
            charts_from_condominium_accounts, migrations.RunPython.noop
        ),
    ]
