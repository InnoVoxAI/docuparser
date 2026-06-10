from __future__ import annotations

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from users.authentication import DocuparseAuthentication
from users.models import Permission


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([IsAuthenticated])
def permissions_list_view(request: Request) -> Response:
    perms = Permission.objects.all().order_by("code")
    return Response([{"code": p.code, "description": p.description} for p in perms])
