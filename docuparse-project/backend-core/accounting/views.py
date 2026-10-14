from __future__ import annotations

from uuid import UUID

from condominiums.models import Condominium
from condominiums.permissions import CondominiumPermission
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from documents.models import Document
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

from accounting.models import LedgerAccount, SupplierRule
from accounting.serializers import (
    DocumentClassificationSerializer,
    LedgerAccountSerializer,
    ManualClassificationSerializer,
    ManualCondominiumSerializer,
    SupplierRuleSerializer,
)
from accounting.services import (
    run_classification_safely,
    set_document_condominium,
    set_manual_classification,
)


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
                {
                    "detail": "Esta conta possui contas filhas ou regras de fornecedor e não pode ser excluída."
                },
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


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def supplier_rules_view(request: Request, condominium_id: UUID) -> Response:
    condominium = get_object_or_404(Condominium, id=condominium_id)
    if request.method == "GET":
        queryset = condominium.supplier_rules.order_by("supplier_tax_id", "keyword")
        return Response(SupplierRuleSerializer(queryset, many=True).data)

    serializer = SupplierRuleSerializer(
        data=request.data, context={"condominium": condominium}
    )
    serializer.is_valid(raise_exception=True)
    rule = serializer.save(condominium=condominium)
    return Response(SupplierRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def supplier_rule_detail_view(
    request: Request, condominium_id: UUID, supplier_rule_id: UUID
) -> Response:
    rule = get_object_or_404(
        SupplierRule.objects.select_related("condominium"),
        id=supplier_rule_id,
        condominium_id=condominium_id,
    )
    if request.method == "GET":
        return Response(SupplierRuleSerializer(rule).data)
    if request.method == "DELETE":
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SupplierRuleSerializer(
        rule,
        data=request.data,
        partial=True,
        context={"condominium": rule.condominium},
    )
    serializer.is_valid(raise_exception=True)
    return Response(SupplierRuleSerializer(serializer.save()).data)


# Depois da decisão do operador o documento segue para o ERP: conta e condomínio
# deixam de ser editáveis.
LOCKED_STATUSES = frozenset(
    {
        Document.Status.APPROVED,
        Document.Status.REJECTED,
        Document.Status.ERP_INTEGRATION_REQUESTED,
        Document.Status.ERP_SENT,
        Document.Status.ERP_FAILED,
    }
)


def _locked_response(document: Document) -> Response | None:
    if document.status not in LOCKED_STATUSES:
        return None
    return Response(
        {
            "detail": "O documento já foi decidido e não aceita mais alterações de classificação."
        },
        status=status.HTTP_409_CONFLICT,
    )


@api_view(["PUT"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("documents.validate")])
def document_ledger_account_view(request: Request, document_id: UUID) -> Response:
    """Operador define ou corrige a conta do documento (classificação manual)."""
    document = get_object_or_404(Document, id=document_id)
    if not request.user.is_authenticated:
        return Response(
            {"detail": "A classificação manual exige um usuário autenticado."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if (locked := _locked_response(document)) is not None:
        return locked
    serializer = ManualClassificationSerializer(
        data=request.data, context={"document": document}
    )
    serializer.is_valid(raise_exception=True)
    classification = set_manual_classification(
        document, serializer.validated_data["ledger_account"], request.user
    )
    return Response(DocumentClassificationSerializer(classification).data)


@api_view(["PUT"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("documents.validate")])
def document_condominium_view(request: Request, document_id: UUID) -> Response:
    """Operador define ou corrige o condomínio; a classificação é refeita nele."""
    document = get_object_or_404(Document, id=document_id)
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Definir o condomínio exige um usuário autenticado."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if (locked := _locked_response(document)) is not None:
        return locked
    serializer = ManualCondominiumSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    condominium = serializer.validated_data["condominium"]
    set_document_condominium(document, condominium, request.user)
    classification = run_classification_safely(document)
    return Response(
        {
            "document_id": str(document.id),
            "condominium_id": str(condominium.id),
            "classification": DocumentClassificationSerializer(classification).data
            if classification
            else None,
        }
    )
