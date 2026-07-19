from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# Fixed UUID used as the singleton pk for per-schema settings models (IntegrationSettings,
# OCRSettings, EmailSettings). Each tenant schema has exactly one row with this id.
SETTINGS_SINGLETON_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def default_openrouter_fallback_model() -> str:
    return settings.OPENROUTER_FALLBACK_MODEL


def default_email_webhook_url() -> str:
    return settings.EMAIL_WEBHOOK_URL


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=64, choices=Status.choices, default=Status.RECEIVED)
    channel = models.CharField(max_length=32)
    file_uri = models.CharField(max_length=1024)
    raw_text_uri = models.CharField(max_length=1024, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    document_type = models.CharField(max_length=64, blank=True)
    layout = models.CharField(max_length=128, blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    received_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    file_valid = models.BooleanField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    ocr_readable = models.BooleanField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["received_at"]),
        ]

    def transition_to(self, status: str) -> None:
        self.status = status
        self.save(update_fields=["status", "updated_at"])


class DocumentEvent(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    event_type = models.CharField(max_length=128, db_index=True)
    event_version = models.CharField(max_length=16, default="v1")
    correlation_id = models.UUIDField(db_index=True)
    source = models.CharField(max_length=128)
    occurred_at = models.DateTimeField()
    payload = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["event_type"]),
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


class ExtractionFieldVersion(TimeStampedModel):
    """Immutable snapshot of extracted fields.

    A new version is created on each extraction, reprocessing, or manual edit.
    At most one version per document is active (the most recent).
    """

    class SourceType(models.TextChoices):
        INITIAL_EXTRACTION = "INITIAL_EXTRACTION", "Initial extraction"
        PROCESSING = "PROCESSING", "Processing"
        REPROCESSING = "REPROCESSING", "Reprocessing"
        MANUAL_EDIT = "MANUAL_EDIT", "Manual edit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="field_versions")
    version_number = models.PositiveIntegerField()
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    fields = models.JSONField(default=dict)
    confidence = models.FloatField(default=0.0)
    previous_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_versions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="extraction_field_versions",
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="unique_field_version_per_document",
            ),
            models.UniqueConstraint(
                fields=["document"],
                condition=models.Q(is_active=True),
                name="unique_active_field_version_per_document",
            ),
        ]
        indexes = [
            models.Index(fields=["document", "version_number"]),
            models.Index(fields=["document", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_id} v{self.version_number} ({self.source_type})"


class ValidationDecision(TimeStampedModel):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CORRECTED = "corrected", "Corrected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="validation_decisions")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="validation_decisions",
    )
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
    approved_export_enabled = models.BooleanField(default=True)
    approved_export_dir = models.CharField(max_length=1024, blank=True)
    approved_export_format = models.CharField(
        max_length=16, choices=ExportFormat.choices, default=ExportFormat.JSON
    )
    superlogica_base_url = models.URLField(blank=True)
    superlogica_mode = models.CharField(
        max_length=32, choices=SuperlogicaMode.choices, default=SuperlogicaMode.DISABLED
    )


class OCRSettings(TimeStampedModel):
    class Engine(models.TextChoices):
        DOCLING = "docling", "Docling"
        OPENROUTER = "openrouter", "OpenRouter"
        TESSERACT = "tesseract", "Tesseract"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    digital_pdf_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.DOCLING)
    scanned_image_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.OPENROUTER)
    handwritten_engine = models.CharField(max_length=32, choices=Engine.choices, default=Engine.OPENROUTER)
    technical_fallback_engine = models.CharField(
        max_length=32, choices=Engine.choices, default=Engine.TESSERACT
    )
    openrouter_model = models.CharField(max_length=255, blank=True)
    openrouter_fallback_model = models.CharField(
        max_length=255, default=default_openrouter_fallback_model
    )
    timeout_seconds = models.PositiveIntegerField(default=120)
    retry_empty_text_enabled = models.BooleanField(default=True)
    digital_pdf_min_text_blocks = models.PositiveIntegerField(default=5)


class EmailSettings(TimeStampedModel):
    class Provider(models.TextChoices):
        IMAP = "imap", "IMAP"
        WEBHOOK = "webhook", "Webhook"
        MANUAL_TEST = "manual_test", "Manual test"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.IMAP)
    inbox_folder = models.CharField(max_length=255, default="INBOX")
    imap_host = models.CharField(max_length=255, blank=True)
    imap_port = models.PositiveIntegerField(default=993)
    username = models.CharField(max_length=255, blank=True)
    webhook_url = models.CharField(max_length=1024, default=default_email_webhook_url)
    accepted_content_types = models.CharField(
        max_length=1024,
        default="application/pdf,image/jpeg,image/png,image/tiff,image/webp",
    )
    max_attachment_mb = models.PositiveIntegerField(default=20)
    blocked_senders = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


class SchemaConfig(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schema_id = models.CharField(max_length=128)
    version = models.CharField(max_length=32)
    definition = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schema_id", "version"],
                name="unique_schema_config_version",
            ),
        ]


class LayoutConfig(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    layout = models.CharField(max_length=128)
    document_type = models.CharField(max_length=64)
    schema_config = models.ForeignKey(SchemaConfig, on_delete=models.PROTECT, related_name="layout_configs")
    confidence_threshold = models.FloatField(default=0.75)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["layout", "document_type"],
                name="unique_layout_config",
            ),
        ]
