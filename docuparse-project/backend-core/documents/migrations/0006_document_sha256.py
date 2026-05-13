from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_emailsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='sha256',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
            preserve_default=False,
        ),
    ]
