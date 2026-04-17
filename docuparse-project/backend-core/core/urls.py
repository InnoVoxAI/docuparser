from django.urls import include, path

urlpatterns = [
    path("api/ocr/", include("documents.urls")),
]
