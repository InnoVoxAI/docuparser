from django.urls import path

from users.permission_views import permissions_list_view
from users.role_views import role_detail_update_delete_view, roles_list_create_view
from users.user_views import user_detail_update_view, users_list_create_view

urlpatterns = [
    path("permissions", permissions_list_view),
    path("roles", roles_list_create_view),
    path("roles/<uuid:role_id>", role_detail_update_delete_view),
    path("users", users_list_create_view),
    path("users/<int:user_id>", user_detail_update_view),
]
