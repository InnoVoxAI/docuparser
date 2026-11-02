"""Executa a sincronização em segundo plano, no mesmo molde do processamento de documentos."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from django.contrib.auth.models import AbstractBaseUser
from django.db import connection

from erp_import import services
from erp_import.factory import administrator_cnpj, build_superlogica_source
from erp_import.history import seed_rules_from_history
from erp_import.models import ImportBatch
from erp_import.sources.base import RegistrySource

logger = logging.getLogger(__name__)

# Janela de despesas lidas para aprender as regras (24 meses).
HISTORY_WINDOW_DAYS = 730

# Uma sincronização por vez já é garantida por `create_batch`; um worker basta.
_executor = ThreadPoolExecutor(max_workers=1)


def start_sync(user: AbstractBaseUser | None) -> ImportBatch:
    """Abre o lote e dispara a leitura da fonte. Levanta `CredentialsError` ou
    `SyncInProgress` sem abrir lote nem chamar a fonte."""
    source = build_superlogica_source()
    batch = services.create_batch(source.source_name, user)
    tenant = connection.tenant
    _executor.submit(_run, batch.pk, tenant, source, administrator_cnpj())
    return batch


def _run(batch_id, tenant: object, source: RegistrySource, admin_cnpj: str) -> None:
    connection.set_tenant(tenant)
    try:
        batch = services.execute_batch(
            ImportBatch.objects.get(pk=batch_id), source, admin_cnpj
        )
        if batch.status == ImportBatch.Status.READY:
            _refresh_rules(source)
    except Exception:
        logger.error("import_sync_worker_failed", exc_info=True)
    finally:
        connection.close()


def _refresh_rules(source: RegistrySource) -> None:
    """Atualiza as regras com o histórico do ERP; falhar aqui nunca desfaz a sincronização."""
    today = date.today()
    try:
        summary = seed_rules_from_history(
            source, today - timedelta(days=HISTORY_WINDOW_DAYS), today
        )
        logger.info("history_rules_refreshed", extra={"expenses": summary.expenses})
    except Exception:
        logger.error("history_rules_refresh_failed", exc_info=True)
