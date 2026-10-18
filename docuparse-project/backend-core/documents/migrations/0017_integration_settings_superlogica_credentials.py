from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0016_document_condominium"),
    ]

    operations = [
        migrations.AddField(
            model_name="integrationsettings",
            name="superlogica_app_token_enc",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="integrationsettings",
            name="superlogica_access_token_enc",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="integrationsettings",
            name="administrator_cnpj",
            field=models.CharField(blank=True, default="", max_length=14),
        ),
    ]
