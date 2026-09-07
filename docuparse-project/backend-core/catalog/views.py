from __future__ import annotations

from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from users.authentication import DocuparseAuthentication

from catalog.defaults import PROTECTED_SCHEMA_IDS
from catalog.models import LayoutConfig, SchemaConfig
from catalog.permissions import CatalogPermission
from catalog.serializers import LayoutConfigSerializer, SchemaConfigSerializer


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CatalogPermission])
def schema_configs_view(request):
    if request.method == "GET":
        queryset = SchemaConfig.objects.all().order_by("schema_id", "version")
        return Response(SchemaConfigSerializer(queryset, many=True).data)

    serializer = SchemaConfigSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    config, created = SchemaConfig.objects.update_or_create(
        schema_id=serializer.validated_data["schema_id"],
        version=serializer.validated_data["version"],
        defaults={
            "definition": serializer.validated_data.get("definition") or {},
            "is_active": serializer.validated_data.get("is_active", True),
        },
    )
    response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response(SchemaConfigSerializer(config).data, status=response_status)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CatalogPermission])
def schema_config_detail_view(request, schema_id):
    config = get_object_or_404(SchemaConfig, id=schema_id)
    if request.method == "GET":
        return Response(SchemaConfigSerializer(config).data)
    if request.method == "DELETE":
        if config.schema_id in PROTECTED_SCHEMA_IDS:
            return Response(
                {"detail": "Este modelo é padrão do sistema e não pode ser excluído."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            config.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": "Este modelo possui layouts vinculados e não pode ser excluído."
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SchemaConfigSerializer(config, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    for field in ("schema_id", "version", "definition", "is_active"):
        if field in serializer.validated_data:
            setattr(config, field, serializer.validated_data[field])
    config.save(
        update_fields=["schema_id", "version", "definition", "is_active", "updated_at"]
    )
    return Response(SchemaConfigSerializer(config).data)


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CatalogPermission])
def layout_configs_view(request):
    if request.method == "GET":
        queryset = LayoutConfig.objects.select_related("schema_config").order_by(
            "layout"
        )
        return Response(LayoutConfigSerializer(queryset, many=True).data)

    serializer = LayoutConfigSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    config = LayoutConfig.objects.create(
        layout=serializer.validated_data["layout"],
        document_type=serializer.validated_data["document_type"],
        schema_config=serializer.validated_data["schema_config"],
        confidence_threshold=serializer.validated_data.get(
            "confidence_threshold", 0.75
        ),
        is_active=serializer.validated_data.get("is_active", True),
    )
    return Response(LayoutConfigSerializer(config).data, status=status.HTTP_201_CREATED)
