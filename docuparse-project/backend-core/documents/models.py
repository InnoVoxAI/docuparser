from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.slug


class UserProfile(TimeStampedModel):
    class Role(models.TextChoices):
        OPERATOR = "operator", "Operator"
        SUPERVISOR = "supervisor", "Supervisor"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="docuparse_profile")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="profiles")
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.OPERATOR)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "user"], name="unique_profile_per_tenant_user"),
        ]


class Document(TimeStampedModel):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        OCR_COMPLETED = "OCR_COMPLETED", "OCR completed"
        OCR_FAILED = "OCR_FAILED", "OCR failed"
        LAYOUT_CLASSIFIED = "LAYOUT_CLASSIFIED", "Layout classified"
        EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED", "Extraction completed"
        VALIDATION_PENDING = "VALIDATION_PENDING", "Validation pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ERP_INTEGRATION_REQUESTED = "ERP_INTEGRATION_REQUESTED", "ERP integration requested"
        ERP_SENT = "ERP_SENT", "ERP sent"
        ERP_FAILED = "ERP_FAILED", "ERP failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="documents")
    status = models.CharField(max_length=64, choices=Status.choices, default=Status.RECEIVED)
    channel = models.CharField(max_length=32)
    file_uri = models.CharField(max_length=1024)
    raw_text_uri = models.CharField(max_length=1024, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    document_type = models.CharField(max_length=64, blank=True)
    layout = models.CharField(max_length=128, blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    received_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "received_at"]),
        ]

    def transition_to(self, status: str) -> None:
        self.status = status
        self.save(update_fields=["status", "updated_at"])


class DocumentEvent(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="document_events")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    event_type = models.CharField(max_length=128, db_index=True)
    event_version = models.CharField(max_length=16, default="v1")
    correlation_id = models.UUIDField(db_index=True)
    source = models.CharField(max_length=128)
    occurred_at = models.DateTimeField()
    payload = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "event_type"]),
            models.Index(fields=["document", "occurred_at"]),
        ]


class ExtractionResult(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name="extraction_result")
    schema_id = models.CharField(max_length=128)
    schema_version = models.CharField(max_length=32)
    fields = models.JSONField(default=dict)
    confidence = models.FloatField(default=0.0)
    requires_human_validation = models.BooleanField(default=True)


class ValidationDecision(TimeStampedModel):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CORRECTED = "corrected", "Corrected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="validation_decisions")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="validation_decisions")
    decision = models.CharField(max_length=32, choices=Decision.choices)
    corrected_fields = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)


class ERPIntegrationAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="erp_attempts")
    connector = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.REQUESTED)
    idempotency_key = models.CharField(max_length=255, unique=True)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    retry_count = models.PositiveIntegerField(default=0)


class IntegrationSettings(TimeStampedModel):
    class ExportFormat(models.TextChoices):
        JSON = "json", "JSON"
        JSONL = "jsonl", "JSONL"

    class SuperlogicaMode(models.TextChoices):
        DISABLED = "disabled", "Disabled"
        MOCK = "mock", "Mock"
        SANDBOX = "sandbox", "Sandbox"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="integration_settings")
    approved_export_enabled = models.BooleanField(default=True)
    approved_export_dir = models.CharField(max_length=1024, blank=True)
    approved_export_format = models.CharField(max_length=16, choices=ExportFormat.choices, default=ExportFormat.JSON)
    superlogica_base_url = models.URLField(blank=True)
    superlogica_mode = models.CharField(max_length=32, choices=SuperlogicaMode.choices, default=SuperlogicaMode.DISABLED)


class OCRSettings(TimeStampedModel):
    class Engine(models.TextChoices):
        DOCLING = "docling", "Docling"
        OPENROUTER = "openrouter", "OpenRouter"
        TESSERACT = "tesseract", "Tesseract"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="ocr_settings")
    digital_pdf_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.DOCLING)
    scanned_image_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.OPENROUTER)
    handwritten_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.OPENROUTER)
    technical_fallback_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.TESSERACT)
    openrouter_model = models.CharField(max_length=255, blank=True)
    openrouter_fallback_model = models.CharField(max_length=255, default="qwen/qwen2.5-vl-72b-instruct")
    timeout_seconds = models.PositiveIntegerField(default=120)
    retry_empty_text_enabled = models.BooleanField(default=True)
    digital_pdf_min_text_blocks = models.PositiveIntegerField(default=5)


class EmailSettings(TimeStampedModel):
    class Provider(models.TextChoices):
        IMAP = "imap", "IMAP"
        WEBHOOK = "webhook", "Webhook"
        MANUAL_TEST = "manual_test", "Manual test"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="email_settings")
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.IMAP)
    inbox_folder = models.CharField(max_length=255, default="INBOX")
    imap_host = models.CharField(max_length=255, blank=True)
    imap_port = models.PositiveIntegerField(default=993)
    username = models.CharField(max_length=255, blank=True)
    webhook_url = models.CharField(max_length=1024, default="http://127.0.0.1:8070/api/v1/email/messages")
    accepted_content_types = models.CharField(
        max_length=1024,
        default="application/pdf,image/jpeg,image/png,image/tiff,image/webp",
    )
    max_attachment_mb = models.PositiveIntegerField(default=20)
    blocked_senders = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


class SchemaConfig(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="schema_configs")
    schema_id = models.CharField(max_length=128)
    version = models.CharField(max_length=32)
    definition = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "schema_id", "version"], name="unique_schema_config_version"),
        ]


class LayoutConfig(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="layout_configs")
    layout = models.CharField(max_length=128)
    document_type = models.CharField(max_length=64)
    schema_config = models.ForeignKey(SchemaConfig, on_delete=models.PROTECT, related_name="layout_configs")
    confidence_threshold = models.FloatField(default=0.75)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "layout", "document_type"], name="unique_layout_config"),
        ]
