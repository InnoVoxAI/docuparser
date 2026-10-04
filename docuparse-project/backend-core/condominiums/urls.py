from django.urls import path

from .views import condominium_detail_view, condominiums_view

urlpatterns = [
    path("condominiums", condominiums_view, name="condominiums"),
    path(
        "condominiums/<uuid:condominium_id>",
        condominium_detail_view,
        name="condominium-detail",
    ),
]
