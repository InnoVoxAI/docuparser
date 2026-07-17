from django.contrib import admin
from django.urls import include, path

# Public URLs: accessible before tenant schema is resolved (login, tenant admin)
# django-tenants serves these from the PUBLIC schema connection.
public_urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.auth_urls")),
    path("api/admin/tenants/", include("tenants.urls")),
]

# Tenant URLs: served only after JWTTenantMiddleware sets the active schema.
# All document-processing and settings endpoints live here.
urlpatterns = public_urlpatterns + [
    path("api/ocr/", include("documents.urls")),
    path("api/ocr/", include("users.users_urls")),
]
