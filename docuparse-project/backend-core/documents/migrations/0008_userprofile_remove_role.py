from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0007_userprofile_role_ref"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="role",
        ),
    ]
