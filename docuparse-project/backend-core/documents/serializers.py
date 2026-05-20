from __future__ import annotations

from rest_framework import serializers
import json

from django.conf import settings
from docuparse_storage import LocalStorage

from documents.models import Document, EmailSettings, ExtractionResult, IntegrationSettings, LayoutConfig, OCRSettings, SchemaConfig, ValidationDecision


class ExtractionResultSerializer(serializers.ModelSerializer):
    fields = serializers.SerializerMethodField(method_name="get_cleaned_fields")

    class Meta:
        model = ExtractionResult
        fields = [
            "schema_id",
            "schema_version",
            "fields",
            "confidence",
            "requires_human_validation",
        ]

    def get_cleaned_fields(self, obj: ExtractionResult) -> dict:
        return {
            key: value
            for key, value in (obj.fields or {}).items()
            if value not in ("", None, [], {}) and not (key == "retencao" and len(str(value)) > 300)
        }


class DocumentListSerializer(serializers.ModelSerializer):
    metadata_channel = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "status",
            "channel",
            "original_filename",
            "content_type",
            "document_type",
            "layout",
            "received_at",
            "updated_at",
            "metadata_channel",
        ]

    def get_metadata_channel(self, obj: Document) -> dict | None:
        return (obj.metadata or {}).get("metadata_channel") or None


class DocumentDetailSerializer(serializers.ModelSerializer):
    extraction_result = ExtractionResultSerializer(read_only=True)
    full_transcription = serializers.SerializerMethodField()
    ocr_metadata = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "tenant_id",
            "status",
            "channel",
            "file_uri",
            "raw_text_uri",
            "original_filename",
            "content_type",
            "size_bytes",
            "document_type",
            "layout",
            "correlation_id",
            "received_at",
            "metadata",
            "extraction_result",
            "full_transcription",
            "ocr_metadata",
            "created_at",
            "updated_at",
        ]

    def get_full_transcription(self, obj: Document) -> str:
        if not obj.raw_text_uri:
            return ""
        try:
            payload = json.loads(LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR).get_bytes(obj.raw_text_uri).decode("utf-8"))
        except (FileNotFoundError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return ""
        return str(payload.get("raw_text") or "")

    def get_ocr_metadata(self, obj: Document) -> dict:
        if not obj.raw_text_uri:
            return {}
        try:
            payload = json.loads(LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR).get_bytes(obj.raw_text_uri).decode("utf-8"))
        except (FileNotFoundError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return {}
        metadata = payload.get("ocr") or {}
        if not metadata:
            metadata = {
                "engine_used": payload.get("engine_used", ""),
                "classification": payload.get("document_type", ""),
                "preprocessing_hint": "",
                "classification_engine_preprocessing_hints": {},
            }
        return metadata


class ValidationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationDecision
        fields = [
            "id",
            "document_id",
            "decided_by_id",
            "decision",
            "corrected_fields",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class IntegrationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationSettings
        fields = [
            "id",
            "tenant_id",
            "approved_export_enabled",
            "approved_export_dir",
            "approved_export_format",
            "superlogica_base_url",
            "superlogica_mode",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant_id", "created_at", "updated_at"]


class OCRSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRSettings
        fields = [
            "id",
            "tenant_id",
            "digital_pdf_engine",
            "scanned_image_engine",
            "handwritten_engine",
            "technical_fallback_engine",
            "openrouter_model",
            "openrouter_fallback_model",
            "timeout_seconds",
            "retry_empty_text_enabled",
            "digital_pdf_min_text_blocks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant_id", "created_at", "updated_at"]


class EmailSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSettings
        fields = [
            "id",
            "tenant_id",
            "provider",
            "inbox_folder",
            "imap_host",
            "imap_port",
            "username",
            "webhook_url",
            "accepted_content_types",
            "max_attachment_mb",
            "blocked_senders",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant_id", "created_at", "updated_at"]


class SchemaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaConfig
        fields = [
            "id",
            "tenant_id",
            "schema_id",
            "version",
            "definition",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LayoutConfigSerializer(serializers.ModelSerializer):
    schema_config_id = serializers.PrimaryKeyRelatedField(
        queryset=SchemaConfig.objects.all(),
        source="schema_config",
    )

    class Meta:
        model = LayoutConfig
        fields = [
            "id",
            "tenant_id",
            "layout",
            "document_type",
            "schema_config_id",
            "confidence_threshold",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
