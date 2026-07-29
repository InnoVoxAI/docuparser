from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="is_platform_role",
            field=models.BooleanField(default=False),
        ),
    ]
