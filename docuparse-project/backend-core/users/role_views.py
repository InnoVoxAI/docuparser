from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from users.authentication import DocuparseAuthentication
from users.models import Permission, Role
from users.permissions import require_permission
from users.serializers import RoleCreateSerializer, RoleListSerializer, RoleUpdateSerializer


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("roles.manage")])
def roles_list_create_view(request: Request) -> Response:
    if request.method == "GET":
        roles = Role.objects.annotate(users_count=Count("user_profiles")).order_by("name")
        return Response(RoleListSerializer(roles, many=True).data)

    serializer = RoleCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    role = Role.objects.create(name=serializer.validated_data["name"])
    perms = Permission.objects.filter(code__in=serializer.validated_data["permission_codes"])
    role.permissions.set(perms)
    role_data = RoleListSerializer(
        Role.objects.annotate(users_count=Count("user_profiles")).get(id=role.id)
    ).data
    return Response(role_data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("roles.manage")])
def role_detail_update_delete_view(request: Request, role_id: str) -> Response:
    role = get_object_or_404(
        Role.objects.annotate(users_count=Count("user_profiles")),
        id=role_id,
    )

    if request.method == "GET":
        return Response(RoleListSerializer(role).data)

    if request.method == "DELETE":
        from documents.models import UserProfile
        users_count = UserProfile.objects.filter(role_ref=role).count()
        if users_count > 0:
            return Response(
                {"detail": f"Esta role está atribuída a {users_count} usuário(s) e não pode ser removida."},
                status=status.HTTP_409_CONFLICT,
            )
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = RoleUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    if "name" in data:
        role.name = data["name"]
        role.save(update_fields=["name", "updated_at"])
    if "permission_codes" in data:
        perms = Permission.objects.filter(code__in=data["permission_codes"])
        role.permissions.set(perms)

    role.refresh_from_db()
    updated = Role.objects.annotate(users_count=Count("user_profiles")).get(id=role.id)
    return Response(RoleListSerializer(updated).data)
