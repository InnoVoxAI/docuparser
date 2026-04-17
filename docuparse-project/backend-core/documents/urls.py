from django.urls import path

from .views import list_engines_view, process_document_view

urlpatterns = [
    path("engines", list_engines_view, name="ocr-engines"),
    path("process", process_document_view, name="ocr-process"),
]
