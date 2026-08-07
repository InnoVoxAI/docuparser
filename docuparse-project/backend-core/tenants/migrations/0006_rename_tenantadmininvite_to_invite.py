import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0005_tenantadmininvite"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="TenantAdminInvite",
            new_name="Invite",
        ),
        migrations.AlterField(
            model_name="invite",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invites",
                to="tenants.tenant",
            ),
        ),
        migrations.AlterField(
            model_name="invite",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invites",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
