from __future__ import annotations

from uuid import UUID

from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response
from users.authentication import DocuparseAuthentication

from condominiums.models import Condominium
from condominiums.permissions import CondominiumPermission
from condominiums.serializers import CondominiumSerializer


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def condominiums_view(request: Request) -> Response:
    if request.method == "GET":
        queryset = Condominium.objects.order_by("name")
        return Response(CondominiumSerializer(queryset, many=True).data)

    serializer = CondominiumSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    condominium = serializer.save()
    return Response(
        CondominiumSerializer(condominium).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def condominium_detail_view(request: Request, condominium_id: UUID) -> Response:
    condominium = get_object_or_404(Condominium, id=condominium_id)
    if request.method == "GET":
        return Response(CondominiumSerializer(condominium).data)
    if request.method == "DELETE":
        try:
            condominium.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": "Este condomínio possui documentos ou regras de fornecedor e não pode ser excluído."
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CondominiumSerializer(condominium, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    return Response(CondominiumSerializer(serializer.save()).data)
