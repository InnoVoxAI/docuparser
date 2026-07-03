from django.urls import path

from tenants.views import tenant_detail_update_view, tenant_list_create_view

urlpatterns = [
    path("", tenant_list_create_view, name="tenant-list-create"),
    path("<slug:slug>/", tenant_detail_update_view, name="tenant-detail-update"),
]
