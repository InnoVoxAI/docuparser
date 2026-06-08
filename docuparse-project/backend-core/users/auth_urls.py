from django.urls import path

from users.auth_views import login_view, logout_view, me_view, refresh_view, register_view

urlpatterns = [
    path("login", login_view),
    path("logout", logout_view),
    path("refresh", refresh_view),
    path("me", me_view),
    path("register", register_view),
]
