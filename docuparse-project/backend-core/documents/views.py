from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services.ocr_client import OCRClient


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
