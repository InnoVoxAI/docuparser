# Generated manually for the DocuParse core domain foundation.

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Document",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("RECEIVED", "Received"), ("OCR_COMPLETED", "OCR completed"), ("OCR_FAILED", "OCR failed"), ("LAYOUT_CLASSIFIED", "Layout classified"), ("EXTRACTION_COMPLETED", "Extraction completed"), ("VALIDATION_PENDING", "Validation pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("ERP_INTEGRATION_REQUESTED", "ERP integration requested"), ("ERP_SENT", "ERP sent"), ("ERP_FAILED", "ERP failed")], default="RECEIVED", max_length=64)),
                ("channel", models.CharField(max_length=32)),
                ("file_uri", models.CharField(max_length=1024)),
                ("raw_text_uri", models.CharField(blank=True, max_length=1024)),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("document_type", models.CharField(blank=True, max_length=64)),
                ("layout", models.CharField(blank=True, max_length=128)),
                ("correlation_id", models.UUIDField(db_index=True, default=uuid.uuid4)),
                ("received_at", models.DateTimeField(default=timezone.now)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="documents.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="SchemaConfig",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("schema_id", models.CharField(max_length=128)),
                ("version", models.CharField(max_length=32)),
                ("definition", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schema_configs", to="documents.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("operator", "Operator"), ("supervisor", "Supervisor"), ("admin", "Admin")], default="operator", max_length=32)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profiles", to="documents.tenant")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="docuparse_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="LayoutConfig",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("layout", models.CharField(max_length=128)),
                ("document_type", models.CharField(max_length=64)),
                ("confidence_threshold", models.FloatField(default=0.75)),
                ("is_active", models.BooleanField(default=True)),
                ("schema_config", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="layout_configs", to="documents.schemaconfig")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="layout_configs", to="documents.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="ExtractionResult",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("schema_id", models.CharField(max_length=128)),
                ("schema_version", models.CharField(max_length=32)),
                ("fields", models.JSONField(default=dict)),
                ("confidence", models.FloatField(default=0.0)),
                ("requires_human_validation", models.BooleanField(default=True)),
                ("document", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="extraction_result", to="documents.document")),
            ],
        ),
        migrations.CreateModel(
            name="ERPIntegrationAttempt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("connector", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("requested", "Requested"), ("sent", "Sent"), ("failed", "Failed")], default="requested", max_length=32)),
                ("idempotency_key", models.CharField(max_length=255, unique=True)),
                ("request_payload", models.JSONField(default=dict)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="erp_attempts", to="documents.document")),
            ],
        ),
        migrations.CreateModel(
            name="DocumentEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_id", models.UUIDField(unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("event_version", models.CharField(default="v1", max_length=16)),
                ("correlation_id", models.UUIDField(db_index=True)),
                ("source", models.CharField(max_length=128)),
                ("occurred_at", models.DateTimeField()),
                ("payload", models.JSONField()),
                ("document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="events", to="documents.document")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="document_events", to="documents.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="ValidationDecision",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(choices=[("approved", "Approved"), ("rejected", "Rejected"), ("corrected", "Corrected")], max_length=32)),
                ("corrected_fields", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True)),
                ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="validation_decisions", to=settings.AUTH_USER_MODEL)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="validation_decisions", to="documents.document")),
            ],
        ),
        migrations.AddIndex(model_name="document", index=models.Index(fields=["tenant", "status"], name="documents_d_tenant__718ecf_idx")),
        migrations.AddIndex(model_name="document", index=models.Index(fields=["tenant", "received_at"], name="documents_d_tenant__5cdd99_idx")),
        migrations.AddIndex(model_name="documentevent", index=models.Index(fields=["tenant", "event_type"], name="documents_d_tenant__2b6fe7_idx")),
        migrations.AddIndex(model_name="documentevent", index=models.Index(fields=["document", "occurred_at"], name="documents_d_documen_10c14b_idx")),
        migrations.AddConstraint(model_name="schemaconfig", constraint=models.UniqueConstraint(fields=("tenant", "schema_id", "version"), name="unique_schema_config_version")),
        migrations.AddConstraint(model_name="userprofile", constraint=models.UniqueConstraint(fields=("tenant", "user"), name="unique_profile_per_tenant_user")),
        migrations.AddConstraint(model_name="layoutconfig", constraint=models.UniqueConstraint(fields=("tenant", "layout", "document_type"), name="unique_layout_config")),
    ]
