from __future__ import annotations

from uuid import UUID

from condominiums.models import Condominium
from condominiums.permissions import CondominiumPermission
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

from accounting.models import LedgerAccount
from accounting.serializers import LedgerAccountSerializer


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def ledger_accounts_view(request: Request, condominium_id: UUID) -> Response:
    condominium = get_object_or_404(Condominium, id=condominium_id)
    if request.method == "GET":
        queryset = condominium.ledger_accounts.order_by("code")
        return Response(LedgerAccountSerializer(queryset, many=True).data)

    serializer = LedgerAccountSerializer(
        data=request.data, context={"condominium": condominium}
    )
    serializer.is_valid(raise_exception=True)
    account = serializer.save(condominium=condominium)
    return Response(
        LedgerAccountSerializer(account).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def ledger_account_detail_view(
    request: Request, condominium_id: UUID, ledger_account_id: UUID
) -> Response:
    account = get_object_or_404(
        LedgerAccount.objects.select_related("condominium"),
        id=ledger_account_id,
        condominium_id=condominium_id,
    )
    if request.method == "GET":
        return Response(LedgerAccountSerializer(account).data)
    if request.method == "DELETE":
        try:
            account.delete()
        except ProtectedError:
            return Response(
                {"detail": "Esta conta possui contas filhas e não pode ser excluída."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = LedgerAccountSerializer(
        account,
        data=request.data,
        partial=True,
        context={"condominium": account.condominium},
    )
    serializer.is_valid(raise_exception=True)
    return Response(LedgerAccountSerializer(serializer.save()).data)
