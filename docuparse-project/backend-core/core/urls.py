from django.urls import include, path

# Public URLs: accessible before tenant schema is resolved (login, tenant admin via API)
# django-tenants serves these from the PUBLIC schema connection.
public_urlpatterns = [
    # AR-07: /admin/ do Django removido (sem uso; sob gunicorn ficava sem estáticos).
    path("api/auth/", include("users.auth_urls")),
    path("api/admin/tenants/", include("tenants.urls")),
]

# Tenant URLs: served only after JWTTenantMiddleware sets the active schema.
# All document-processing and settings endpoints live here.
urlpatterns = public_urlpatterns + [
    path("api/ocr/", include("catalog.urls")),
    path("api/ocr/", include("condominiums.urls")),
    path("api/ocr/", include("accounting.urls")),
    path("api/ocr/", include("erp_import.urls")),
    path("api/ocr/", include("documents.urls")),
    path("api/ocr/", include("users.users_urls")),
]
