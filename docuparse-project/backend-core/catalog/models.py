from __future__ import annotations

import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SchemaConfig(TimeStampedModel):
    """Definição de extração de um tipo de documento. Catálogo global (schema
    `public`) — antes vivia em `documents` (por-tenant). Ver spec 018."""

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
    """Mapeia um `layout`/`document_type` para o `SchemaConfig` que o extrai.
    Catálogo global — ver spec 018."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    layout = models.CharField(max_length=128)
    document_type = models.CharField(max_length=64)
    schema_config = models.ForeignKey(
        SchemaConfig, on_delete=models.PROTECT, related_name="layout_configs"
    )
    confidence_threshold = models.FloatField(default=0.75)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["layout", "document_type"],
                name="unique_layout_config",
            ),
        ]
