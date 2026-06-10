from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from users.authentication import DocuparseAuthentication
from users.permissions import require_permission
from users.serializers import UserCreateSerializer, UserListSerializer, UserUpdateSerializer

User = get_user_model()


def last_admin_guard(user_id: int) -> bool:
    """Return True (guard triggered) if deactivating user_id leaves zero active admins."""
    from documents.models import UserProfile
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
        from documents.models import UserProfile
        users = (
            User.objects
            .select_related("docuparse_profile__role_ref")
            .prefetch_related("docuparse_profile__role_ref__permissions")
            .order_by("first_name", "username")
        )
        return Response(UserListSerializer(users, many=True).data)

    serializer = UserCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)


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
            {"detail": "Não é possível desativar o último administrador ativo do sistema."},
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
        profile.role_ref = data["role_id"]
        profile.save(update_fields=["role_ref", "updated_at"])

    user.refresh_from_db()
    return Response(UserListSerializer(user).data)
