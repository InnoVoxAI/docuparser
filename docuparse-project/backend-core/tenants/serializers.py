from __future__ import annotations

import re

from rest_framework import serializers

from tenants.models import Tenant


class TenantSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    name = serializers.CharField(read_only=True)
    schema_name = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class TenantCreateSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)

    def validate_slug(self, value: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", value):
            raise serializers.ValidationError(
                "Slug must contain only lowercase letters, digits, and hyphens."
            )
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                f"A tenant with slug '{value}' already exists."
            )
        return value


class TenantUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    is_active = serializers.BooleanField(required=False)
