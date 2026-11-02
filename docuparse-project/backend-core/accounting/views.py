from __future__ import annotations

import logging
from uuid import UUID

from condominiums.models import Condominium
from condominiums.permissions import CondominiumPermission
from django.db.models import ExpressionWrapper, F, FloatField, ProtectedError, Q
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

from accounting.learning import learn_from_choice
from accounting.models import ChartOfAccounts, LedgerAccount, SupplierRule
from accounting.serializers import (
    ChartOfAccountsSerializer,
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
from accounting.suggestions import suggest_accounts

logger = logging.getLogger(__name__)


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def charts_of_accounts_view(request: Request) -> Response:
    if request.method == "GET":
        queryset = ChartOfAccounts.objects.order_by("name")
        return Response(ChartOfAccountsSerializer(queryset, many=True).data)

    serializer = ChartOfAccountsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    chart = serializer.save()
    return Response(
        ChartOfAccountsSerializer(chart).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def chart_of_accounts_detail_view(request: Request, chart_id: UUID) -> Response:
    chart = get_object_or_404(ChartOfAccounts, id=chart_id)
    if request.method == "GET":
        return Response(ChartOfAccountsSerializer(chart).data)
    if request.method == "DELETE":
        try:
            chart.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": "Este plano possui contas ou condomínios e não pode ser excluído."
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ChartOfAccountsSerializer(chart, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    return Response(ChartOfAccountsSerializer(serializer.save()).data)


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def ledger_accounts_view(request: Request, chart_id: UUID) -> Response:
    chart = get_object_or_404(ChartOfAccounts, id=chart_id)
    if request.method == "GET":
        queryset = chart.accounts.order_by("code")
        return Response(LedgerAccountSerializer(queryset, many=True).data)

    serializer = LedgerAccountSerializer(data=request.data, context={"chart": chart})
    serializer.is_valid(raise_exception=True)
    account = serializer.save(chart=chart)
    return Response(
        LedgerAccountSerializer(account).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def ledger_account_detail_view(
    request: Request, chart_id: UUID, ledger_account_id: UUID
) -> Response:
    account = get_object_or_404(
        LedgerAccount.objects.select_related("chart"),
        id=ledger_account_id,
        chart_id=chart_id,
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
        context={"chart": account.chart},
    )
    serializer.is_valid(raise_exception=True)
    return Response(LedgerAccountSerializer(serializer.save()).data)


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def condominium_ledger_accounts_view(
    request: Request, condominium_id: UUID
) -> Response:
    """Contas do plano do condomínio (lista vazia se ele ainda não tem plano)."""
    condominium = get_object_or_404(Condominium, id=condominium_id)
    queryset = LedgerAccount.objects.filter(
        chart_id=condominium.chart_of_accounts_id
    ).order_by("code")
    return Response(LedgerAccountSerializer(queryset, many=True).data)


def _no_chart_response() -> Response:
    return Response(
        {"detail": "O condomínio não tem plano de contas."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _paginated_chart_rules(request: Request, chart: ChartOfAccounts) -> Response:
    """Regras do plano com busca e filtros: `search`, `origin`, `prefills`, `is_active`, `limit`, `offset`."""
    params = request.query_params
    queryset = chart.supplier_rules.filter(condominium__isnull=True).select_related(
        "ledger_account"
    )
    if search := params.get("search", "").strip():
        digits = "".join(c for c in search if c.isdigit())
        match = (
            Q(keyword__icontains=search)
            | Q(ledger_account__name__icontains=search)
            | Q(ledger_account__code__startswith=search)
        )
        queryset = queryset.filter(
            match | Q(supplier_tax_id__contains=digits) if digits else match
        )
    if origin := params.get("origin"):
        queryset = queryset.filter(origin=origin)
    if params.get("is_active") in ("true", "false"):
        queryset = queryset.filter(is_active=params["is_active"] == "true")
    if params.get("prefills") in ("true", "false"):
        clear = Q(origin=SupplierRule.Origin.MANUAL) | Q(
            evidence_total__gte=SupplierRule.MIN_HISTORY_EVIDENCE,
            evidence_count__gte=ExpressionWrapper(
                F("evidence_total") * SupplierRule.MIN_HISTORY_AGREEMENT,
                output_field=FloatField(),
            ),
        )
        applies = clear & Q(is_active=True, ledger_account__is_active=True)
        queryset = queryset.filter(
            applies if params["prefills"] == "true" else ~applies
        )
    queryset = queryset.order_by("-evidence_total", "supplier_tax_id", "keyword", "id")
    try:
        limit = min(max(int(params.get("limit", 50)), 1), 200)
        offset = max(int(params.get("offset", 0)), 0)
    except ValueError:
        limit, offset = 50, 0
    return Response(
        {
            "count": queryset.count(),
            "results": SupplierRuleSerializer(
                queryset[offset : offset + limit], many=True
            ).data,
        }
    )


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def chart_supplier_rules_view(request: Request, chart_id: UUID) -> Response:
    """Regras de fornecedor que valem para todos os condomínios do plano."""
    chart = get_object_or_404(ChartOfAccounts, id=chart_id)
    if request.method == "GET":
        return _paginated_chart_rules(request, chart)

    serializer = SupplierRuleSerializer(data=request.data, context={"chart": chart})
    serializer.is_valid(raise_exception=True)
    rule = serializer.save(chart=chart, condominium=None)
    return Response(SupplierRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def chart_supplier_rule_detail_view(
    request: Request, chart_id: UUID, supplier_rule_id: UUID
) -> Response:
    rule = get_object_or_404(
        SupplierRule.objects.select_related("chart"),
        id=supplier_rule_id,
        chart_id=chart_id,
        condominium__isnull=True,
    )
    return _rule_detail(request, rule, {"chart": rule.chart})


@api_view(["GET", "POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def supplier_rules_view(request: Request, condominium_id: UUID) -> Response:
    """Regras só deste condomínio: valem no lugar das do plano."""
    condominium = get_object_or_404(Condominium, id=condominium_id)
    if request.method == "GET":
        queryset = condominium.supplier_rules.order_by("supplier_tax_id", "keyword")
        return Response(SupplierRuleSerializer(queryset, many=True).data)
    if condominium.chart_of_accounts is None:
        return _no_chart_response()

    serializer = SupplierRuleSerializer(
        data=request.data,
        context={"chart": condominium.chart_of_accounts, "condominium": condominium},
    )
    serializer.is_valid(raise_exception=True)
    rule = serializer.save(chart=condominium.chart_of_accounts, condominium=condominium)
    return Response(SupplierRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def supplier_rule_detail_view(
    request: Request, condominium_id: UUID, supplier_rule_id: UUID
) -> Response:
    rule = get_object_or_404(
        SupplierRule.objects.select_related("chart", "condominium"),
        id=supplier_rule_id,
        condominium_id=condominium_id,
    )
    return _rule_detail(
        request, rule, {"chart": rule.chart, "condominium": rule.condominium}
    )


def _rule_detail(request: Request, rule: SupplierRule, context: dict) -> Response:
    if request.method == "GET":
        return Response(SupplierRuleSerializer(rule).data)
    if request.method == "DELETE":
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SupplierRuleSerializer(
        rule, data=request.data, partial=True, context=context
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
    document = get_object_or_404(
        Document.objects.select_related("condominium"), id=document_id
    )
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
    # Aprender com a escolha nunca pode impedir a classificação.
    try:
        learn_from_choice(
            document,
            serializer.validated_data["ledger_account"],
            serializer.validated_data["remember"],
        )
    except Exception:
        logger.error(
            "learning_failed", exc_info=True, extra={"document_id": str(document.id)}
        )
    return Response(DocumentClassificationSerializer(classification).data)


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("inbox.view")])
def document_account_suggestions_view(request: Request, document_id: UUID) -> Response:
    """Contas que o fornecedor do documento já usou, com a evidência de cada uma."""
    document = get_object_or_404(
        Document.objects.select_related("condominium"), id=document_id
    )
    return Response(suggest_accounts(document))


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
