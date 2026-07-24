from django.urls import path

from tenants.views import (
    tenant_detail_update_view,
    tenant_list_create_view,
    tenant_switch_view,
    tenant_users_view,
)

urlpatterns = [
    path("", tenant_list_create_view, name="tenant-list-create"),
    path("<slug:slug>/", tenant_detail_update_view, name="tenant-detail-update"),
    path("<slug:slug>/users/", tenant_users_view, name="tenant-users"),
    path("<slug:slug>/switch/", tenant_switch_view, name="tenant-switch"),
]
