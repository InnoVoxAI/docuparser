from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)

# Logadas só como [SET]/[EMPTY] — o valor nunca vai para o log.
_SECRET_ENVS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "SECRET_KEY",
    "DOCUPARSE_INTERNAL_SERVICE_TOKEN",
    "OPENROUTER_API_KEY",
)


def _mask_url_credentials(url: str) -> str:
    """Remove user:password embutidos numa URL antes de logá-la (ex.: REDIS_URL)."""
    if not url:
        return ""
    parsed = urlsplit(url)
    if not parsed.password:
        return url
    netloc = f"{parsed.username or ''}:***@{parsed.hostname or ''}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def log_startup_config() -> None:
    """Imprime a config resolvida no boot, para tornar visível divergência de env
    entre ambientes (ConfigMap/Secret) sem precisar de shell no pod.

    Os valores não-secretos saem com ``repr()`` de propósito: é o que revela aspas
    literais e espaços sobrando vindos de um ConfigMap. ``BACKEND_OCR_URL`` e
    ``LANGEXTRACT_SERVICE_URL`` não passam por ``strip()`` em settings.py, então
    ' http://host ' vira uma URL inválida só descoberta lá no fundo da thread.
    """
    from django.conf import settings

    values = {
        "BACKEND_OCR_URL": settings.BACKEND_OCR_URL,
        "LANGEXTRACT_SERVICE_URL": settings.LANGEXTRACT_SERVICE_URL,
        "DOCUPARSE_STORAGE_BACKEND": settings.DOCUPARSE_STORAGE_BACKEND,
        "S3_ENDPOINT_URL": settings.S3_ENDPOINT_URL,
        "S3_BUCKET": settings.S3_BUCKET,
        "S3_REGION": settings.S3_REGION,
        "DOCUPARSE_AUTO_PROCESS_OCR": settings.DOCUPARSE_AUTO_PROCESS_OCR,
        "DOCUPARSE_AUTO_PROCESS_EXTRACTION": settings.DOCUPARSE_AUTO_PROCESS_EXTRACTION,
        "DOCUPARSE_EVENT_BUS": os.environ.get("DOCUPARSE_EVENT_BUS", ""),
        "REDIS_URL": _mask_url_credentials(os.environ.get("REDIS_URL", "")),
    }

    logger.info("startup: ===== backend-core resolved config =====")
    for key, value in values.items():
        logger.info("startup: config %s = %r", key, value)
    for key in _SECRET_ENVS:
        state = "[SET]" if os.environ.get(key, "").strip() else "[EMPTY]"
        logger.info("startup: config %s = %s", key, state)
    logger.info("startup: ========================================")


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
