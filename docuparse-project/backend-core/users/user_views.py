from __future__ import annotations

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response
from tenants.invites import create_invite

from users.authentication import DocuparseAuthentication
from users.permissions import require_permission
from users.serializers import (
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


def last_admin_guard(user_id: int) -> bool:
    """Return True (guard triggered) if deactivating user_id leaves zero active admins."""
    from tenants.models import UserProfile

    admins_after = (
        UserProfile.objects.filter(
            user__is_active=True,
            role_ref__permissions__code="users.manage",
        )
        .filter(role_ref__permissions__code="roles.manage")
        .exclude(user_id=user_id)
        .distinct()
        .count()
    )
    return admins_after == 0


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("users.manage")])
def users_list_create_view(request: Request) -> Response:
    if request.method == "GET":
        tenant = getattr(request, "tenant", None)
        qs = User.objects.select_related(
            "docuparse_profile__role_ref"
        ).prefetch_related("docuparse_profile__role_ref__permissions")
        if tenant is not None:
            qs = qs.filter(docuparse_profile__tenant=tenant)
        return Response(
            UserListSerializer(qs.order_by("first_name", "username"), many=True).data
        )

    serializer = UserCreateSerializer(data=request.data)
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
    email = data["email"]
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

    try:
        invite = create_invite(
            tenant=request.tenant,
            name=data["name"],
            email=email,
            role=data["role_id"],
        )
    except Exception:
        return Response(
            {
                "data": None,
                "error": {
                    "code": "INVITE_DELIVERY_FAILED",
                    "detail": "Usuário criado, mas o convite não pôde ser enviado. Use o reenvio de convite.",
                },
                "meta": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    created_user = User.objects.select_related("docuparse_profile__role_ref").get(
        pk=invite.user_id
    )
    return Response(
        {
            "data": UserListSerializer(created_user).data,
            "error": None,
            "meta": {"invite_sent": True},
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("users.manage")])
def user_detail_update_view(request: Request, user_id: int) -> Response:
    user = get_object_or_404(
        User.objects.select_related("docuparse_profile__role_ref"),
        pk=user_id,
    )

    if request.method == "GET":
        return Response(UserListSerializer(user).data)

    serializer = UserUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Guard: prevent deactivating the last admin
    if data.get("is_active") is False and last_admin_guard(user_id):
        return Response(
            {
                "detail": "Não é possível desativar o último administrador ativo do sistema."
            },
            status=status.HTTP_409_CONFLICT,
        )

    if "name" in data:
        user.first_name = data["name"]
    if "email" in data:
        user.email = data["email"]
        user.username = data["email"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    user.save()

    profile = getattr(user, "docuparse_profile", None)
    if profile and "role_id" in data and data["role_id"] is not None:
        new_role = data["role_id"]
        if new_role.is_platform_role:
            actor_profile = getattr(request.user, "docuparse_profile", None)
            if (
                not actor_profile
                or not actor_profile.role_ref
                or not actor_profile.role_ref.is_platform_role
            ):
                return Response(
                    {
                        "detail": "Você não tem permissão para atribuir roles de plataforma."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        profile.role_ref = new_role
        profile.save(update_fields=["role_ref", "updated_at"])

    user.refresh_from_db()
    return Response(UserListSerializer(user).data)
