from __future__ import annotations

from rest_framework import serializers

from catalog.models import LayoutConfig, SchemaConfig


class SchemaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaConfig
        fields = [
            "id",
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
            "layout",
            "document_type",
            "schema_config_id",
            "confidence_threshold",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
