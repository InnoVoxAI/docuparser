from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from users.authentication import DocuparseAuthentication
from users.permissions import require_permission

from tenants.models import Tenant
from tenants.serializers import TenantCreateSerializer, TenantSerializer, TenantUpdateSerializer


def _provision_tenant(data: dict) -> tuple[Tenant | None, Response | None]:
    """Create the Tenant record and its PostgreSQL schema. Returns (tenant, None) on success."""
    slug = data["slug"]
    try:
        with transaction.atomic():
            tenant = Tenant(slug=slug, name=data["name"], schema_name=f"tenant_{slug}", is_active=True)
            tenant.save()
        return tenant, None
    except Exception:
        return None, Response(
            {
                "data": None,
                "error": {"code": "SCHEMA_CREATION_FAILED", "detail": "Schema creation failed; rollback complete."},
                "meta": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("tenants.manage")])
def tenant_list_create_view(request: Request) -> Response:
    if request.method == "GET":
        tenants = Tenant.objects.all().order_by("name")
        return Response({
            "data": TenantSerializer(tenants, many=True).data,
            "error": None,
            "meta": {"count": tenants.count()},
        })

    serializer = TenantCreateSerializer(data=request.data)
    if not serializer.is_valid():
        errors = serializer.errors
        slug_errors = errors.get("slug", [])
        if any("already exists" in str(e) for e in slug_errors):
            return Response(
                {"data": None, "error": {"code": "TENANT_EXISTS", "detail": f"Tenant slug '{request.data.get('slug')}' already exists."}, "meta": {}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"data": None, "error": {"code": "VALIDATION_ERROR", "detail": errors}, "meta": {}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tenant, err = _provision_tenant(serializer.validated_data)
    if err is not None:
        return err
    return Response(
        {"data": TenantSerializer(tenant).data, "error": None, "meta": {}},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("tenants.manage")])
def tenant_detail_update_view(request: Request, slug: str) -> Response:
    try:
        tenant = Tenant.objects.get(slug=slug)
    except Tenant.DoesNotExist:
        return Response(
            {
                "data": None,
                "error": {"code": "TENANT_NOT_FOUND", "detail": f"No tenant with slug '{slug}'."},
                "meta": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response({"data": TenantSerializer(tenant).data, "error": None, "meta": {}})

    serializer = TenantUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(
            {"data": None, "error": {"code": "VALIDATION_ERROR", "detail": serializer.errors}, "meta": {}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data

    if data.get("is_active") is False:
        remaining = Tenant.objects.filter(is_active=True).exclude(slug=slug).count()
        if remaining == 0:
            return Response(
                {
                    "data": None,
                    "error": {"code": "LAST_TENANT", "detail": "Cannot deactivate the only active tenant."},
                    "meta": {},
                },
                status=status.HTTP_409_CONFLICT,
            )

    if "name" in data:
        tenant.name = data["name"]
    if "is_active" in data:
        tenant.is_active = data["is_active"]
    tenant.save(update_fields=[k for k in ("name", "is_active") if k in data] + ["updated_at"])

    return Response({"data": TenantSerializer(tenant).data, "error": None, "meta": {}})
