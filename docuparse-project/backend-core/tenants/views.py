from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from users.authentication import DocuparseAuthentication
from users.permissions import require_permission

from django.contrib.auth import get_user_model

from tenants.models import Tenant
from tenants.serializers import TenantCreateSerializer, TenantSerializer, TenantUpdateSerializer


def _provision_tenant(data: dict) -> tuple[Tenant | None, Response | None]:
    """Create the Tenant record, PostgreSQL schema, and a default admin user."""
    import os
    from users.models import Role
    from tenants.models import UserProfile

    slug = data["slug"]
    try:
        with transaction.atomic():
            tenant = Tenant(slug=slug, name=data["name"], schema_name=f"tenant_{slug}", is_active=True)
            tenant.save()
    except Exception:
        return None, Response(
            {
                "data": None,
                "error": {"code": "SCHEMA_CREATION_FAILED", "detail": "Schema creation failed; rollback complete."},
                "meta": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Seed a default admin user for the new tenant using the same credentials
    # convention as seed_data: admin@<slug>.<ADMIN_EMAIL domain>.
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    tenant_admin_email = f"admin@{slug}"

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=tenant_admin_email,
        defaults={"email": tenant_admin_email, "is_active": True, "is_staff": False},
    )
    if created:
        user.set_password(admin_password)
        user.save()

    admin_role = Role.objects.filter(name="admin").first()
    UserProfile.objects.get_or_create(user=user, defaults={"tenant": tenant, "role_ref": admin_role})

    return tenant, None


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
        from tenants.models import UserProfile
        try:
            requester_slug = UserProfile.objects.select_related("tenant").get(user=request.user).tenant.slug
            if requester_slug == slug:
                return Response(
                    {
                        "data": None,
                        "error": {"code": "OWN_TENANT", "detail": "Cannot deactivate your own tenant."},
                        "meta": {},
                    },
                    status=status.HTTP_409_CONFLICT,
                )
        except UserProfile.DoesNotExist:
            pass

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


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("tenants.manage")])
def tenant_users_view(request: Request, slug: str) -> Response:
    """List or create users belonging to a specific tenant (public-schema operation)."""
    try:
        tenant = Tenant.objects.get(slug=slug)
    except Tenant.DoesNotExist:
        return Response(
            {"data": None, "error": {"code": "TENANT_NOT_FOUND", "detail": f"No tenant with slug '{slug}'."}, "meta": {}},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        from tenants.models import UserProfile
        profiles = UserProfile.objects.filter(tenant=tenant).select_related("user", "role_ref")
        data = [
            {
                "id": p.user.pk,
                "name": p.user.first_name or p.user.username,
                "email": p.user.email,
                "is_active": p.user.is_active,
                "role": {"id": str(p.role_ref.id), "name": p.role_ref.name} if p.role_ref else None,
            }
            for p in profiles
        ]
        return Response({"data": data, "error": None, "meta": {"count": len(data)}})

    # POST — create a user and assign them to this tenant
    User = get_user_model()
    name = str(request.data.get("name", "")).strip()
    email = str(request.data.get("email", "")).strip()
    password = str(request.data.get("password", ""))
    role_id = request.data.get("role_id")

    if not all([name, email, password, role_id]):
        return Response(
            {"data": None, "error": {"code": "VALIDATION_ERROR", "detail": "name, email, password e role_id são obrigatórios."}, "meta": {}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=email).exists():
        return Response(
            {"data": None, "error": {"code": "USER_EXISTS", "detail": f"E-mail '{email}' já está em uso."}, "meta": {}},
            status=status.HTTP_409_CONFLICT,
        )

    from users.models import Role
    try:
        role = Role.objects.get(id=role_id)
    except (Role.DoesNotExist, Exception):
        return Response(
            {"data": None, "error": {"code": "ROLE_NOT_FOUND", "detail": "Role não encontrada."}, "meta": {}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=email, email=email, password=password, first_name=name, is_active=True,
    )
    from tenants.models import UserProfile
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)

    return Response(
        {"data": {"id": user.pk, "name": user.first_name, "email": user.email, "is_active": user.is_active}, "error": None, "meta": {}},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("tenants.manage")])
def tenant_switch_view(request: Request, slug: str) -> Response:
    """Issue a new JWT whose tenant claim is set to the requested slug.

    The caller's UserProfile is unchanged — only the token context switches.
    """
    try:
        tenant = Tenant.objects.get(slug=slug, is_active=True)
    except Tenant.DoesNotExist:
        return Response(
            {"data": None, "error": {"code": "TENANT_NOT_FOUND", "detail": f"Tenant '{slug}' não encontrado ou inativo."}, "meta": {}},
            status=status.HTTP_404_NOT_FOUND,
        )

    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(request.user)
    refresh["tenant"] = tenant.slug

    return Response({"data": {"access": str(refresh.access_token), "refresh": str(refresh)}, "error": None, "meta": {}})
