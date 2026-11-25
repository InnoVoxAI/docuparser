"""API do lançamento no ERP: estado, confirmação do analista e reenvio."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from users.authentication import DocuparseAuthentication
from users.permissions import request_has_permission, require_permission

from documents.models import Document
from documents.services.erp_flow import (
    ErpFlowError,
    confirm_send,
    erp_detail,
    retry_send,
)


def _body(request, detail: dict) -> dict:
    """Acrescenta se este usuário pode enviar ao ERP, para a tela mostrar ou não os botões."""
    return {**detail, "can_send": request_has_permission(request, "erp.send")}


def _error_response(exc: ErpFlowError) -> Response:
    body = {"detail": str(exc), "code": exc.code}
    if exc.errors:
        body["errors"] = exc.errors
    return Response(body, status=exc.status)


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("inbox.view")])
def document_erp_view(request, document_id):
    """Estado do lançamento no ERP e o resumo do que será enviado."""
    document = get_object_or_404(Document, id=document_id)
    return Response(_body(request, erp_detail(document)))


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("erp.send")])
def document_erp_confirm_view(request, document_id):
    """O analista confirma o envio da despesa ao ERP."""
    document = get_object_or_404(Document, id=document_id)
    try:
        detail = confirm_send(document, request.user)
        return Response(_body(request, detail), status=http_status.HTTP_202_ACCEPTED)
    except ErpFlowError as exc:
        return _error_response(exc)


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([require_permission("erp.send")])
def document_erp_retry_view(request, document_id):
    """Reenvio de uma falha retentável, respeitando a espera entre tentativas."""
    document = get_object_or_404(Document, id=document_id)
    try:
        detail = retry_send(document, request.user)
        return Response(_body(request, detail), status=http_status.HTTP_202_ACCEPTED)
    except ErpFlowError as exc:
        return _error_response(exc)
