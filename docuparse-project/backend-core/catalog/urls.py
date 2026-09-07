from django.urls import path

from .views import (
    layout_configs_view,
    schema_config_detail_view,
    schema_configs_view,
)

# Mesmas strings de path de hoje — o catálogo virou global, mas o contrato REST
# não muda (spec 018, contracts/catalog-endpoints.md).
urlpatterns = [
    path("schema-configs", schema_configs_view, name="schema-configs"),
    path(
        "schema-configs/<uuid:schema_id>",
        schema_config_detail_view,
        name="schema-config-detail",
    ),
    path("layout-configs", layout_configs_view, name="layout-configs"),
]
