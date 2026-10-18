from __future__ import annotations

from uuid import UUID

from condominiums.permissions import CondominiumPermission
from django.db.models import Count
from django.shortcuts import get_object_or_404
from documents.models import SETTINGS_SINGLETON_ID, IntegrationSettings
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response
from users.authentication import DocuparseAuthentication

from erp_import import services
from erp_import.background import start_sync
from erp_import.credentials import CredentialsError, credentials_configured
from erp_import.factory import build_superlogica_source
from erp_import.models import ImportBatch, ImportProposal
from erp_import.serializers import (
    BulkDecisionSerializer,
    ImportBatchSerializer,
    ImportProposalSerializer,
    ResolveSerializer,
)
from erp_import.services import InvalidDecision, SyncInProgress
from erp_import.sources.base import SourceError

P = ImportProposal
DEFAULT_LIMIT, MAX_LIMIT = 200, 1000


def _conflict(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_409_CONFLICT)


def _needs_user(request: Request) -> Response | None:
    if request.user.is_authenticated:
        return None
    return Response(
        {"detail": "Decidir uma proposta exige um usuário autenticado."},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_overview_view(request: Request) -> Response:
    """Estado da importação: credenciais, último lote e o que espera decisão."""
    config = IntegrationSettings.objects.filter(id=SETTINGS_SINGLETON_ID).first()
    latest = (
        ImportBatch.objects.select_related("started_by").order_by("-created_at").first()
    )
    pending = (
        P.objects.filter(status=P.Status.PENDING)
        .values("entity_type", "action")
        .annotate(total=Count("id"))
    )
    by_action = {action: 0 for action in P.Action.values}
    by_entity = {entity: 0 for entity in P.EntityType.values}
    for row in pending:
        by_action[row["action"]] += row["total"]
        by_entity[row["entity_type"]] += row["total"]
    return Response(
        {
            "credentials_configured": credentials_configured(config),
            "latest_batch": ImportBatchSerializer(latest).data if latest else None,
            "pending_by_action": by_action,
            "pending_by_entity": by_entity,
        }
    )


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_sync_view(request: Request) -> Response:
    user_error = _needs_user(request)
    if user_error:
        return user_error
    try:
        batch = start_sync(request.user)
    except CredentialsError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except SyncInProgress as exc:
        return _conflict(str(exc))
    return Response(ImportBatchSerializer(batch).data, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_test_connection_view(request: Request) -> Response:
    """Uma leitura simples para validar os tokens salvos."""
    try:
        build_superlogica_source().check_connection()
    except (CredentialsError, SourceError) as exc:
        return Response({"ok": False, "detail": str(exc)})
    return Response({"ok": True, "detail": ""})


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_proposals_view(request: Request) -> Response:
    params = request.query_params
    queryset = P.objects.select_related("decided_by").filter(
        status=params.get("status", P.Status.PENDING)
    )
    for field in ("entity_type", "action", "batch_id"):
        if params.get(field):
            queryset = queryset.filter(**{field: params[field]})
    queryset = queryset.order_by("entity_type", "action", "external_id")

    try:
        limit = min(int(params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(params.get("offset", 0)), 0)
    except ValueError:
        return Response(
            {"detail": "limit e offset precisam ser números."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {
            "count": queryset.count(),
            "results": ImportProposalSerializer(
                queryset[offset : offset + limit], many=True
            ).data,
        }
    )


def _decide_single(request: Request, proposal_id: UUID, decision: str) -> Response:
    user_error = _needs_user(request)
    if user_error:
        return user_error
    proposal = get_object_or_404(P, id=proposal_id)
    try:
        if decision == "resolve":
            serializer = ResolveSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            resolved = services.resolve(
                proposal, request.user, serializer.validated_data["resolution"]
            )
            return Response(ImportProposalSerializer(resolved, many=True).data)
        action = services.approve if decision == "approve" else services.reject
        return Response(ImportProposalSerializer(action(proposal, request.user)).data)
    except InvalidDecision as exc:
        return _conflict(str(exc))


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_proposal_approve_view(request: Request, proposal_id: UUID) -> Response:
    return _decide_single(request, proposal_id, "approve")


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_proposal_reject_view(request: Request, proposal_id: UUID) -> Response:
    return _decide_single(request, proposal_id, "reject")


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_proposal_resolve_view(request: Request, proposal_id: UUID) -> Response:
    return _decide_single(request, proposal_id, "resolve")


def _decide_many(request: Request, target: str) -> Response:
    user_error = _needs_user(request)
    if user_error:
        return user_error
    serializer = BulkDecisionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    proposals = list(P.objects.filter(id__in=serializer.validated_data["ids"]))
    result = services.decide_many(proposals, request.user, target)
    return Response(
        {
            "done": ImportProposalSerializer(result.done, many=True).data,
            "failed": [
                {"id": str(p.id), "detail": detail} for p, detail in result.failed
            ],
        }
    )


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_proposals_approve_view(request: Request) -> Response:
    return _decide_many(request, P.Status.APPROVED)


@api_view(["POST"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([CondominiumPermission])
def import_proposals_reject_view(request: Request) -> Response:
    return _decide_many(request, P.Status.REJECTED)
