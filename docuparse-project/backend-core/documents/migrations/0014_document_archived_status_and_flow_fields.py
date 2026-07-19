# Generated for feature 014-bpmn-worker-flow-update

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_alter_emailsettings_webhook_url_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.CharField(
                choices=[
                    ('RECEIVED', 'Received'),
                    ('OCR_COMPLETED', 'OCR completed'),
                    ('OCR_FAILED', 'OCR failed'),
                    ('LAYOUT_CLASSIFIED', 'Layout classified'),
                    ('EXTRACTION_COMPLETED', 'Extraction completed'),
                    ('VALIDATION_PENDING', 'Validation pending'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                    ('ERP_INTEGRATION_REQUESTED', 'ERP integration requested'),
                    ('ERP_SENT', 'ERP sent'),
                    ('ERP_FAILED', 'ERP failed'),
                    ('ARCHIVED', 'Archived'),
                ],
                default='RECEIVED',
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='file_valid',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='rejection_reason',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='document',
            name='ocr_readable',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
