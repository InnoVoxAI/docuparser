"""API de leitura dos processos de pagamento (agrupamento de NF e boletos)."""

from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from users.authentication import DocuparseAuthentication
from users.permissions import require_permission

from documents.models import PaymentProcess
from documents.pagination import paginate_queryset
from documents.payment_serializers import PaymentProcessSerializer
from documents.services.payment_processes import (
    PaymentProcessError,
    confirm_process,
    reject_process,
)


def _queryset():
    return PaymentProcess.objects.select_related(
        "invoice", "decided_by"
    ).prefetch_related("boletos")


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("inbox.view")])
def payment_processes_view(request):
    """Lista paginada. Filtros: `status`, `origin` e `document_id` (nota ou boleto)."""
    queryset = _queryset()
    status_value = request.query_params.get("status")
    if status_value:
        if status_value not in PaymentProcess.Status.values:
            return Response(
                {"detail": f"status inválido: {status_value!r}"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        queryset = queryset.filter(status=status_value)
    origin_value = request.query_params.get("origin")
    if origin_value:
        if origin_value not in PaymentProcess.Origin.values:
            return Response(
                {"detail": f"origin inválido: {origin_value!r}"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        queryset = queryset.filter(origin=origin_value)
    document_id = request.query_params.get("document_id")
    if document_id:
        queryset = queryset.filter(
            Q(invoice_id=document_id) | Q(boletos=document_id)
        ).distinct()

    page = paginate_queryset(queryset, request)
    serialized = PaymentProcessSerializer(page.items, many=True).data
    return Response(page.envelope(serialized))


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("inbox.view")])
def payment_process_detail_view(request, process_id):
    process = get_object_or_404(_queryset(), id=process_id)
    return Response(PaymentProcessSerializer(process).data)


def _decide(request, process_id, decision):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "A decisão exige um usuário autenticado."},
            status=http_status.HTTP_403_FORBIDDEN,
        )
    get_object_or_404(PaymentProcess, id=process_id)
    try:
        process = decision(process_id, request.user)
    except PaymentProcessError as exc:
        code_status = {
            "no_boletos": http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        }.get(exc.code, http_status.HTTP_409_CONFLICT)
        return Response({"detail": str(exc), "code": exc.code}, status=code_status)
    process = _queryset().get(pk=process.pk)
    return Response(PaymentProcessSerializer(process).data)


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("documents.validate")])
def payment_process_confirm_view(request, process_id):
    """Operador confirma o agrupamento sugerido (ou montado à mão)."""
    return _decide(request, process_id, confirm_process)


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("documents.validate")])
def payment_process_reject_view(request, process_id):
    """Operador rejeita: os documentos voltam ao pool de documentos sem match."""
    return _decide(request, process_id, reject_process)
