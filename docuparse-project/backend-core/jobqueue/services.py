"""Enfileiramento na fila durável.

O AR-32 só usa o `enqueue` para encadear `ocr` → `extraction` dentro do worker.
O AR-31 o liga às rotas (document-received, ERP, retry de etapa e reprocess).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from django.db import connection
from django.utils import timezone
from django_tenants.utils import get_public_schema_name
from psycopg2.extras import Json

from jobqueue.models import ProcessingJob
from jobqueue.policy import policy_for

_ACTIVE = "('queued', 'running')"


def _table() -> str:
    return f'"{get_public_schema_name()}"."{ProcessingJob._meta.db_table}"'


def enqueue(
    document: Any,
    step: str,
    *,
    triggered_by: str = "",
    payload: dict[str, Any] | None = None,
    run_after: datetime | None = None,
    orchestration_run_id: str = "",
    tenant_schema: str | None = None,
) -> tuple[ProcessingJob, bool]:
    """Cria um job `queued` para `(tenant, documento, etapa)` ou devolve o ativo.

    Devolve `(job, created)`. `document` é um `Document` ou o seu id (UUID).
    O tenant vem de `connection.tenant`, a não ser que `tenant_schema` seja
    passado. Usa a conexão e a transação correntes: o search_path do
    django-tenants inclui o `public`, então o job e as gravações no schema do
    tenant entram no mesmo commit.

    A idempotência é o `INSERT … ON CONFLICT DO NOTHING` sobre o índice único
    parcial `jobqueue_one_active_job_per_step` (no máximo um job queued/running
    por etapa). Num conflito, devolve o job ativo que já existia.
    """
    schema = tenant_schema or getattr(connection, "schema_name", None)
    if not schema or schema == get_public_schema_name():
        raise ValueError(
            "enqueue precisa de um tenant: chame com connection.set_tenant(...) "
            "ou passe tenant_schema"
        )
    document_id = getattr(document, "pk", document)
    if not isinstance(document_id, uuid.UUID):
        document_id = uuid.UUID(str(document_id))

    policy = policy_for(step)
    now = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {_table()} (
                tenant_schema, document_id, step, status, attempts, max_attempts,
                run_after, locked_by, last_error_type, last_error_message,
                orchestration_run_id, triggered_by, payload, created_at, updated_at
            ) VALUES (%s, %s, %s, 'queued', 0, %s, %s, '', '', '', %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_schema, document_id, step)
                WHERE status IN {_ACTIVE}
            DO NOTHING
            RETURNING id
            """,
            [
                schema,
                document_id,
                step,
                policy.max_attempts,
                run_after or now,
                orchestration_run_id,
                triggered_by or "",
                Json(payload or {}),
                now,
                now,
            ],
        )
        row = cursor.fetchone()

    if row is not None:
        return ProcessingJob.objects.get(pk=row[0]), True
    existing = ProcessingJob.objects.get(
        tenant_schema=schema,
        document_id=document_id,
        step=step,
        status__in=ProcessingJob.ACTIVE_STATUSES,
    )
    return existing, False
