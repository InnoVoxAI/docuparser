"""API de leitura dos processos de pagamento (agrupamento de NF e boletos)."""

from __future__ import annotations

from django.core.exceptions import ValidationError
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
from documents.payment_serializers import (
    PaymentDocumentSerializer,
    PaymentProcessSerializer,
)
from documents.services.payment_manual import (
    create_manual_process,
    undo_manual_process,
    unmatched_documents,
)
from documents.services.payment_processes import (
    PaymentProcessError,
    confirm_process,
    reject_process,
)
from documents.views import _apply_search


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
        return _error_response(exc)
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


_ERROR_STATUS = {
    "no_boletos": http_status.HTTP_422_UNPROCESSABLE_ENTITY,
    "wrong_kind": http_status.HTTP_400_BAD_REQUEST,
    "not_found": http_status.HTTP_404_NOT_FOUND,
}


def _error_response(exc: PaymentProcessError) -> Response:
    code_status = _ERROR_STATUS.get(exc.code, http_status.HTTP_409_CONFLICT)
    return Response({"detail": str(exc), "code": exc.code}, status=code_status)


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("inbox.view")])
def payment_candidates_view(request):
    """Notas fiscais ou boletos sem match, para o pareamento manual.

    Parâmetros: `kind` (`invoice` ou `boleto`, obrigatório), `search`, `page`, `page_size`.
    """
    kind = request.query_params.get("kind")
    if kind not in ("invoice", "boleto"):
        return Response(
            {"detail": "kind deve ser 'invoice' ou 'boleto'."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    queryset = _apply_search(
        unmatched_documents(kind), request.query_params.get("search")
    )
    page = paginate_queryset(queryset, request)
    serialized = PaymentDocumentSerializer(page.items, many=True).data
    return Response(page.envelope(serialized))


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("documents.validate")])
def payment_process_create_view(request):
    """Operador monta o par à mão: `{invoice_id, boleto_ids}`. O agrupamento nasce pendente."""
    invoice_id = request.data.get("invoice_id")
    boleto_ids = request.data.get("boleto_ids")
    if not invoice_id or not isinstance(boleto_ids, list):
        return Response(
            {"detail": "Informe invoice_id e a lista boleto_ids."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    try:
        process = create_manual_process(invoice_id, boleto_ids)
    except (ValidationError, ValueError):
        return Response(
            {"detail": "Identificador de documento inválido."},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    except PaymentProcessError as exc:
        return _error_response(exc)
    process = _queryset().get(pk=process.pk)
    return Response(
        PaymentProcessSerializer(process).data, status=http_status.HTTP_201_CREATED
    )


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("documents.validate")])
def payment_process_undo_view(request, process_id):
    """Desfaz a seleção manual ainda pendente: os documentos voltam ao pool."""
    get_object_or_404(PaymentProcess, id=process_id)
    try:
        undo_manual_process(process_id)
    except PaymentProcessError as exc:
        return _error_response(exc)
    return Response(status=http_status.HTTP_204_NO_CONTENT)
