from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response
from users.authentication import DocuparseAuthentication
from users.permissions import require_permission

from tenants.invites import (
    InviteAlreadyUsedError,
    InviteExpiredError,
    InviteNotFoundError,
    activate_invite,
    create_admin_invite,
)
from tenants.models import Tenant, UserProfile
from tenants.serializers import (
    TenantCreateSerializer,
    TenantSerializer,
    TenantUpdateSerializer,
)


def _provision_tenant(data: dict) -> tuple[Tenant | None, Response | None]:
    """Create the Tenant record, PostgreSQL schema, and its admin invite."""
    slug = data["slug"]

    try:
        with transaction.atomic():
            tenant = Tenant(
                slug=slug,
                name=data["name"],
                schema_name=f"tenant_{slug}",
                is_active=True,
            )
            tenant.save()
    except Exception:
        return None, Response(
            {
                "data": None,
                "error": {
                    "code": "SCHEMA_CREATION_FAILED",
                    "detail": "Schema creation failed; rollback complete.",
                },
                "meta": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        create_admin_invite(tenant, data["admin_name"], data["admin_email"])
    except Exception:
        # Email delivery failure does NOT roll back the tenant/user already
        # created above — the operator is expected to use the resend endpoint.
        return tenant, Response(
            {
                "data": None,
                "error": {
                    "code": "INVITE_DELIVERY_FAILED",
                    "detail": "Tenant criado, mas o convite não pôde ser enviado. Use o reenvio de convite.",
                },
                "meta": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return tenant, None


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("tenants.manage")])
def tenant_list_create_view(request: Request) -> Response:
    if request.method == "GET":
        tenants = Tenant.objects.all().order_by("name")
        return Response(
            {
                "data": TenantSerializer(tenants, many=True).data,
                "error": None,
                "meta": {"count": tenants.count()},
            }
        )

    serializer = TenantCreateSerializer(data=request.data)
    if not serializer.is_valid():
        errors = serializer.errors
        slug_errors = errors.get("slug", [])
        if any("already exists" in str(e) for e in slug_errors):
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "TENANT_EXISTS",
                        "detail": f"Tenant slug '{request.data.get('slug')}' already exists.",
                    },
                    "meta": {},
                },
                status=status.HTTP_409_CONFLICT,
            )
        admin_email_errors = errors.get("admin_email", [])
        if any("já está em uso" in str(e) for e in admin_email_errors):
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "ADMIN_EMAIL_IN_USE",
                        "detail": f"E-mail '{request.data.get('admin_email')}' já está em uso por outra conta.",
                    },
                    "meta": {},
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "data": None,
                "error": {"code": "VALIDATION_ERROR", "detail": errors},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    tenant, err = _provision_tenant(serializer.validated_data)
    if err is not None:
        return err
    return Response(
        {
            "data": TenantSerializer(tenant).data,
            "error": None,
            "meta": {"admin_invite_sent": True},
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def invite_activate_view(request: Request, token: str) -> Response:
    password = request.data.get("password", "")

    try:
        user = activate_invite(token, password)
    except InviteNotFoundError:
        return Response(
            {
                "data": None,
                "error": {"code": "INVITE_NOT_FOUND", "detail": "Convite inválido."},
                "meta": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    except InviteAlreadyUsedError:
        return Response(
            {
                "data": None,
                "error": {
                    "code": "INVITE_ALREADY_USED",
                    "detail": "Este convite já foi utilizado.",
                },
                "meta": {},
            },
            status=status.HTTP_410_GONE,
        )
    except InviteExpiredError:
        return Response(
            {
                "data": None,
                "error": {
                    "code": "INVITE_EXPIRED",
                    "detail": "Este convite expirou. Solicite um novo ao administrador da plataforma.",
                },
                "meta": {},
            },
            status=status.HTTP_410_GONE,
        )
    except DjangoValidationError as exc:
        return Response(
            {
                "data": None,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "detail": {"password": exc.messages},
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = UserProfile.objects.select_related("tenant").get(user=user)
    return Response(
        {
            "data": {"email": user.email, "tenant_slug": profile.tenant.slug},
            "error": None,
            "meta": {},
        }
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
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "detail": f"No tenant with slug '{slug}'.",
                },
                "meta": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(
            {"data": TenantSerializer(tenant).data, "error": None, "meta": {}}
        )

    serializer = TenantUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(
            {
                "data": None,
                "error": {"code": "VALIDATION_ERROR", "detail": serializer.errors},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data

    if data.get("is_active") is False:
        from tenants.models import UserProfile

        try:
            requester_slug = (
                UserProfile.objects.select_related("tenant")
                .get(user=request.user)
                .tenant.slug
            )
            if requester_slug == slug:
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "OWN_TENANT",
                            "detail": "Cannot deactivate your own tenant.",
                        },
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
                    "error": {
                        "code": "LAST_TENANT",
                        "detail": "Cannot deactivate the only active tenant.",
                    },
                    "meta": {},
                },
                status=status.HTTP_409_CONFLICT,
            )

    if "name" in data:
        tenant.name = data["name"]
    if "is_active" in data:
        tenant.is_active = data["is_active"]
    tenant.save(
        update_fields=[k for k in ("name", "is_active") if k in data] + ["updated_at"]
    )

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
            {
                "data": None,
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "detail": f"No tenant with slug '{slug}'.",
                },
                "meta": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        from tenants.models import UserProfile

        profiles = UserProfile.objects.filter(tenant=tenant).select_related(
            "user", "role_ref"
        )
        data = [
            {
                "id": p.user.pk,
                "name": p.user.first_name or p.user.username,
                "email": p.user.email,
                "is_active": p.user.is_active,
                "role": {"id": str(p.role_ref.id), "name": p.role_ref.name}
                if p.role_ref
                else None,
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
            {
                "data": None,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "detail": "name, email, password e role_id são obrigatórios.",
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=email).exists():
        return Response(
            {
                "data": None,
                "error": {
                    "code": "USER_EXISTS",
                    "detail": f"E-mail '{email}' já está em uso.",
                },
                "meta": {},
            },
            status=status.HTTP_409_CONFLICT,
        )

    from users.models import Role

    try:
        role = Role.objects.get(id=role_id)
    except (Role.DoesNotExist, Exception):
        return Response(
            {
                "data": None,
                "error": {"code": "ROLE_NOT_FOUND", "detail": "Role não encontrada."},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name,
        is_active=True,
    )
    from tenants.models import UserProfile

    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)

    return Response(
        {
            "data": {
                "id": user.pk,
                "name": user.first_name,
                "email": user.email,
                "is_active": user.is_active,
            },
            "error": None,
            "meta": {},
        },
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
            {
                "data": None,
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "detail": f"Tenant '{slug}' não encontrado ou inativo.",
                },
                "meta": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(request.user)
    refresh["tenant"] = tenant.slug

    return Response(
        {
            "data": {"access": str(refresh.access_token), "refresh": str(refresh)},
            "error": None,
            "meta": {},
        }
    )
