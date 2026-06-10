from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("users.auth_urls")),
    path("api/ocr/", include("documents.urls")),
    path("api/ocr/", include("users.users_urls")),
]
