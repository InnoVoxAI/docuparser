"""Fonte única de verdade do catálogo global de tipos de documento.

Substitui as duas listas divergentes de antes (`documents/startup.py` e
`users/.../seed_data.py`). Consumida por:
- `catalog/migrations/0002_seed_default_catalog.py` (seed em `public`);
- `users/management/commands/seed_data.py` (fresh install);
- `catalog/management/commands/check_catalog_divergence.py` (allow-list).
"""

from __future__ import annotations

from typing import Any, TypedDict

# schema_ids que não podem ser excluídos via API (são padrão do sistema).
PROTECTED_SCHEMA_IDS = ["nota_fiscal_default", "conta_agua_default"]


class SchemaSpec(TypedDict):
    schema_id: str
    version: str
    definition: dict[str, Any]


class LayoutSpec(TypedDict):
    layout: str
    document_type: str
    schema_id: str


class CatalogSpecs(TypedDict):
    schemas: list[SchemaSpec]
    layouts: list[LayoutSpec]


def default_catalog_specs() -> CatalogSpecs:
    """Lê as definições canônicas de `models/*/definition.py` e devolve o
    conjunto canônico do catálogo global: 2 schemas + 3 layouts."""
    import models.contadeagua.definition as _agua_def
    import models.nota_fiscal.definition as _nf_def

    schemas: list[SchemaSpec] = [
        {
            "schema_id": _nf_def.SCHEMA_ID,
            "version": _nf_def.VERSION,
            "definition": _nf_def.EXTRACTION_DEFINITION,
        },
        {
            "schema_id": _agua_def.SCHEMA_ID,
            "version": _agua_def.VERSION,
            "definition": _agua_def.EXTRACTION_DEFINITION,
        },
    ]
    layouts: list[LayoutSpec] = [
        {
            "layout": "nota_fiscal",
            "document_type": "",
            "schema_id": _nf_def.SCHEMA_ID,
        },
        {
            "layout": "fatura_condominio",
            "document_type": "",
            "schema_id": _agua_def.SCHEMA_ID,
        },
        {
            "layout": "fatura_energia",
            "document_type": "",
            "schema_id": _agua_def.SCHEMA_ID,
        },
    ]
    return {"schemas": schemas, "layouts": layouts}


def seed_default_catalog(schema_config_model=None, layout_config_model=None) -> None:
    """Popula o catálogo global de forma idempotente (FR-007, FR-009).

    Aceita os modelos por parâmetro para uso em data migrations
    (``apps.get_model``); por padrão usa os modelos reais.
    """
    if schema_config_model is None or layout_config_model is None:
        from catalog.models import LayoutConfig, SchemaConfig

        schema_config_model = schema_config_model or SchemaConfig
        layout_config_model = layout_config_model or LayoutConfig

    specs = default_catalog_specs()

    schema_by_id: dict[str, Any] = {}
    for spec in specs["schemas"]:
        obj, _ = schema_config_model.objects.update_or_create(
            schema_id=spec["schema_id"],
            version=spec["version"],
            defaults={"definition": spec["definition"], "is_active": True},
        )
        schema_by_id[spec["schema_id"]] = obj

    for lc in specs["layouts"]:
        schema = schema_by_id.get(lc["schema_id"])
        if schema is None:
            continue
        layout_config_model.objects.get_or_create(
            layout=lc["layout"],
            document_type=lc["document_type"],
            defaults={"schema_config": schema, "is_active": True},
        )
