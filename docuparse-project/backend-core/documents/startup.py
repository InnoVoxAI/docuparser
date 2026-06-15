from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ensure_default_schemas() -> None:
    from documents.models import SchemaConfig, Tenant
    import models.nota_fiscal.definition as _nf_def
    import models.contadeagua.definition as _agua_def

    tenant = Tenant.objects.filter(name="default").first()
    if tenant is None:
        logger.warning("startup: default tenant not found — skipping default schema creation")
        return

    specs = [
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

    for spec in specs:
        _, created = SchemaConfig.objects.update_or_create(
            tenant=tenant,
            schema_id=spec["schema_id"],
            version=spec["version"],
            defaults={"definition": spec["definition"], "is_active": True},
        )
        action = "created" if created else "updated"
        logger.info("startup: %s schema %s", action, spec["schema_id"])
