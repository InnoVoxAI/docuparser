from django.contrib.auth import get_user_model
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.http import Http404
from django.http import FileResponse
from io import BytesIO
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from docuparse_events import event_bus_from_env
from docuparse_storage import LocalStorage

from .models import Document, EmailSettings, IntegrationSettings, LayoutConfig, OCRSettings, SchemaConfig, Tenant, ValidationDecision
from .serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    EmailSettingsSerializer,
    IntegrationSettingsSerializer,
    LayoutConfigSerializer,
    OCRSettingsSerializer,
    SchemaConfigSerializer,
    ValidationDecisionSerializer,
)
from .services.ocr_client import OCRClient
from .services.erp_publisher import publish_erp_integration_requested
from .services.event_consumers import consume_document_received
from .services.dlq_inspector import DEFAULT_DLQ_STREAMS, requeue_dlq_entry, inspect_dlq_streams
from .services.ocr_processor import process_document_ocr, start_document_ocr_thread


@require_GET
def health_view(request):
    return JsonResponse({"status": "healthy", "service": "docuparse-backend-core"})


@require_GET
def ready_view(request):
    return JsonResponse({"status": "ready", "service": "docuparse-backend-core"})


def _internal_token_error(request):
    token = settings.DOCUPARSE_INTERNAL_SERVICE_TOKEN
    if not token:
        return None
    if request.headers.get("Authorization") == f"Bearer {token}":
        return None
    return Response({"detail": "invalid internal service token"}, status=status.HTTP_401_UNAUTHORIZED)


@require_GET
def list_engines_view(request):
    # Simple pass-through endpoint used by the frontend dropdown.
    try:
        client = OCRClient()
        engines = client.list_engines()
        return JsonResponse({"engines": engines})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=502)


@csrf_exempt
@require_POST
def process_document_view(request):
    # Accept file + selected engine, then orchestrate backend-ocr processing.
    uploaded_file = request.FILES.get("file")
    engine = request.POST.get("engine")

    if uploaded_file is None:
        return JsonResponse({"error": "Field 'file' is required"}, status=400)

    try:
        client = OCRClient()
        result = client.process_document(
            file_obj=uploaded_file.file,
            filename=uploaded_file.name,
            engine=engine,
        )
        return JsonResponse(result)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=502)


@api_view(["GET"])
def documents_inbox_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    queryset = Document.objects.select_related("tenant").order_by("-received_at")
    status_filter = request.query_params.get("status")
    tenant_filter = request.query_params.get("tenant")
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if tenant_filter:
        queryset = queryset.filter(tenant__slug=tenant_filter)
    return Response(DocumentListSerializer(queryset[:200], many=True).data)


@api_view(["POST"])
def document_received_event_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    document = consume_document_received(request.data)
    if settings.DOCUPARSE_AUTO_PROCESS_OCR and not document.raw_text_uri:
        start_document_ocr_thread(document.id)
    return Response(DocumentDetailSerializer(document).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def document_detail_view(request, document_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    document = get_object_or_404(
        Document.objects.select_related("tenant").prefetch_related("events"),
        id=document_id,
    )
    return Response(DocumentDetailSerializer(document).data)


@api_view(["DELETE"])
def document_delete_view(request, document_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    document = get_object_or_404(Document, id=document_id)
    document.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def document_file_view(request, document_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    document = get_object_or_404(Document, id=document_id)
    try:
        content = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR).get_bytes(document.file_uri)
    except (FileNotFoundError, ValueError) as exc:
        raise Http404("Document file not found") from exc
    return FileResponse(
        BytesIO(content),
        content_type=document.content_type or "application/octet-stream",
        filename=document.original_filename or f"{document.id}",
    )


@api_view(["POST"])
def document_process_ocr_view(request, document_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    try:
        document = process_document_ocr(document_id)
    except (FileNotFoundError, ValueError) as exc:
        return Response({"detail": f"Arquivo original nao encontrado: {exc}"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({"detail": f"Falha no OCR: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(DocumentDetailSerializer(document).data)


@api_view(["POST"])
def document_reprocess_ocr_view(request, document_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    try:
        document = process_document_ocr(document_id)
    except (FileNotFoundError, ValueError) as exc:
        return Response({"detail": f"Arquivo original nao encontrado: {exc}"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({"detail": f"Falha no reprocessamento OCR: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(DocumentDetailSerializer(document).data)


@api_view(["POST"])
def document_validation_view(request, document_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    document = get_object_or_404(Document, id=document_id)
    decision = request.data.get("decision")
    if decision not in {
        ValidationDecision.Decision.APPROVED,
        ValidationDecision.Decision.REJECTED,
        ValidationDecision.Decision.CORRECTED,
    }:
        return Response({"detail": "Invalid decision"}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.data.get("decided_by_id")
    user = get_object_or_404(get_user_model(), id=user_id) if user_id else get_user_model().objects.first()
    if user is None:
        return Response({"detail": "A user is required to validate documents"}, status=status.HTTP_400_BAD_REQUEST)

    validation = ValidationDecision.objects.create(
        document=document,
        decided_by=user,
        decision=decision,
        corrected_fields=request.data.get("corrected_fields") or {},
        notes=request.data.get("notes") or "",
    )

    corrected_fields = request.data.get("corrected_fields") or {}
    if corrected_fields and hasattr(document, "extraction_result"):
        document.extraction_result.fields = corrected_fields
        document.extraction_result.requires_human_validation = False
        document.extraction_result.save(update_fields=["fields", "requires_human_validation", "updated_at"])

    if decision == ValidationDecision.Decision.APPROVED:
        document.transition_to(Document.Status.APPROVED)
        publish_erp_integration_requested(document)
    elif decision == ValidationDecision.Decision.REJECTED:
        document.transition_to(Document.Status.REJECTED)
    else:
        document.transition_to(Document.Status.VALIDATION_PENDING)

    return Response(ValidationDecisionSerializer(validation).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def schema_configs_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    if request.method == "GET":
        queryset = SchemaConfig.objects.select_related("tenant").order_by("schema_id", "version")
        return Response(SchemaConfigSerializer(queryset, many=True).data)

    tenant = _tenant_from_request(request)
    serializer = SchemaConfigSerializer(data={**request.data, "tenant_id": str(tenant.id)})
    serializer.is_valid(raise_exception=True)
    config = SchemaConfig.objects.create(
        tenant=tenant,
        schema_id=serializer.validated_data["schema_id"],
        version=serializer.validated_data["version"],
        definition=serializer.validated_data.get("definition") or {},
        is_active=serializer.validated_data.get("is_active", True),
    )
    return Response(SchemaConfigSerializer(config).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def schema_config_detail_view(request, schema_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    config = get_object_or_404(SchemaConfig.objects.select_related("tenant"), id=schema_id)
    if request.method == "GET":
        return Response(SchemaConfigSerializer(config).data)

    serializer = SchemaConfigSerializer(config, data={**request.data, "tenant_id": str(config.tenant_id)}, partial=True)
    serializer.is_valid(raise_exception=True)
    for field in ("schema_id", "version", "definition", "is_active"):
        if field in serializer.validated_data:
            setattr(config, field, serializer.validated_data[field])
    config.save(update_fields=["schema_id", "version", "definition", "is_active", "updated_at"])
    return Response(SchemaConfigSerializer(config).data)


@api_view(["GET", "POST"])
def layout_configs_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    if request.method == "GET":
        queryset = LayoutConfig.objects.select_related("tenant", "schema_config").order_by("layout")
        return Response(LayoutConfigSerializer(queryset, many=True).data)

    tenant = _tenant_from_request(request)
    serializer = LayoutConfigSerializer(data={**request.data, "tenant_id": str(tenant.id)})
    serializer.is_valid(raise_exception=True)
    config = LayoutConfig.objects.create(
        tenant=tenant,
        layout=serializer.validated_data["layout"],
        document_type=serializer.validated_data["document_type"],
        schema_config=serializer.validated_data["schema_config"],
        confidence_threshold=serializer.validated_data.get("confidence_threshold", 0.75),
        is_active=serializer.validated_data.get("is_active", True),
    )
    return Response(LayoutConfigSerializer(config).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def integration_settings_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    tenant_slug = request.query_params.get("tenant") or request.data.get("tenant_slug") or "tenant-demo"
    tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_slug})
    config, _ = IntegrationSettings.objects.get_or_create(
        tenant=tenant,
        defaults={
            "approved_export_dir": settings.DOCUPARSE_APPROVED_EXPORT_DIR,
        },
    )
    if request.method == "GET":
        return Response(IntegrationSettingsSerializer(config).data)

    serializer = IntegrationSettingsSerializer(config, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    for field in (
        "approved_export_enabled",
        "approved_export_dir",
        "approved_export_format",
        "superlogica_base_url",
        "superlogica_mode",
    ):
        if field in serializer.validated_data:
            setattr(config, field, serializer.validated_data[field])
    config.save(
        update_fields=[
            "approved_export_enabled",
            "approved_export_dir",
            "approved_export_format",
            "superlogica_base_url",
            "superlogica_mode",
            "updated_at",
        ]
    )
    return Response(IntegrationSettingsSerializer(config).data)


@api_view(["GET", "PATCH"])
def ocr_settings_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    tenant_slug = request.query_params.get("tenant") or request.data.get("tenant_slug") or "tenant-demo"
    tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_slug})
    config, _ = OCRSettings.objects.get_or_create(tenant=tenant)
    if request.method == "GET":
        return Response(OCRSettingsSerializer(config).data)

    serializer = OCRSettingsSerializer(config, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    for field in (
        "digital_pdf_engine",
        "scanned_image_engine",
        "handwritten_engine",
        "technical_fallback_engine",
        "openrouter_model",
        "openrouter_fallback_model",
        "timeout_seconds",
        "retry_empty_text_enabled",
        "digital_pdf_min_text_blocks",
    ):
        if field in serializer.validated_data:
            setattr(config, field, serializer.validated_data[field])
    config.save(
        update_fields=[
            "digital_pdf_engine",
            "scanned_image_engine",
            "handwritten_engine",
            "technical_fallback_engine",
            "openrouter_model",
            "openrouter_fallback_model",
            "timeout_seconds",
            "retry_empty_text_enabled",
            "digital_pdf_min_text_blocks",
            "updated_at",
        ]
    )
    return Response(OCRSettingsSerializer(config).data)


@api_view(["GET", "PATCH"])
def email_settings_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    tenant_slug = request.query_params.get("tenant") or request.data.get("tenant_slug") or "tenant-demo"
    tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_slug})
    config, _ = EmailSettings.objects.get_or_create(tenant=tenant)
    if request.method == "GET":
        return Response(EmailSettingsSerializer(config).data)

    serializer = EmailSettingsSerializer(config, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    for field in (
        "provider",
        "inbox_folder",
        "imap_host",
        "imap_port",
        "username",
        "webhook_url",
        "accepted_content_types",
        "max_attachment_mb",
        "blocked_senders",
        "is_active",
    ):
        if field in serializer.validated_data:
            setattr(config, field, serializer.validated_data[field])
    config.save(
        update_fields=[
            "provider",
            "inbox_folder",
            "imap_host",
            "imap_port",
            "username",
            "webhook_url",
            "accepted_content_types",
            "max_attachment_mb",
            "blocked_senders",
            "is_active",
            "updated_at",
        ]
    )
    return Response(EmailSettingsSerializer(config).data)


@api_view(["GET"])
def dlq_summary_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    limit = _positive_int(request.query_params.get("limit"), default=50, maximum=500)
    report = inspect_dlq_streams(
        event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR),
        streams=DEFAULT_DLQ_STREAMS,
        limit=limit,
    )
    return Response(
        {
            "total": sum(item["count"] for item in report),
            "streams": [
                {
                    "stream": item["stream"],
                    "count": item["count"],
                    "latest": item["entries"][-1] if item["entries"] else None,
                }
                for item in report
            ],
        }
    )


@api_view(["GET"])
def dlq_events_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    stream = request.query_params.get("stream") or "ocr.completed.dlq"
    if stream not in DEFAULT_DLQ_STREAMS:
        return Response({"detail": "Invalid DLQ stream"}, status=status.HTTP_400_BAD_REQUEST)
    limit = _positive_int(request.query_params.get("limit"), default=50, maximum=500)
    report = inspect_dlq_streams(
        event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR),
        streams=[stream],
        limit=limit,
    )[0]
    return Response(report)


@api_view(["POST"])
def dlq_requeue_view(request):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    stream = request.data.get("stream")
    entry_id = request.data.get("id") or request.data.get("entry_id")
    if not stream or not entry_id:
        return Response({"detail": "Fields 'stream' and 'id' are required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = requeue_dlq_entry(
            event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR),
            stream=stream,
            entry_id=str(entry_id),
            target_stream=request.data.get("target_stream") or None,
            note=request.data.get("note") or "",
            requested_by=request.data.get("requested_by") or "api",
            execute=bool(request.data.get("execute")),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_202_ACCEPTED if result["execute"] else status.HTTP_200_OK)


def _tenant_from_request(request) -> Tenant:
    tenant_slug = request.data.get("tenant") or request.data.get("tenant_slug") or "tenant-demo"
    tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_slug})
    return tenant


def _positive_int(value, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 1), maximum)
