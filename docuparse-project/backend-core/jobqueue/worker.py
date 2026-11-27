"""Worker da fila durável (AR-32).

Um processo, três tipos de thread:

- **main**: a do comando `run_worker`. Recebe SIGTERM/SIGINT (o comando liga
  os handlers a `Worker.stop`), espera os jobs em curso até o prazo de parada e
  devolve 0.
- **N threads de trabalho** (`--concurrency`): cada uma faz um loop de claim →
  troca de tenant → despacho → finalização, com a própria conexão.
- **heartbeat**: a cada 15 s, atualiza `heartbeat_at` dos jobs deste processo e
  grava o arquivo de liveness (`/tmp/worker-alive`) se as threads de trabalho
  estiverem vivas. O banco fora do ar não impede a liveness: reiniciar o pod
  não o traz de volta.

O claim usa `UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED LIMIT 1)`
sobre o índice parcial `jobqueue_claim_idx`, então dois workers nunca pegam o
mesmo job. Quem repete uma etapa é a fila: um erro transitório volta a `queued`
com `run_after = now() + backoff(attempts)`. Um job que não terminou no prazo
de parada fica `running` sem heartbeat e volta pela recuperação do AR-34.
Até o AR-33, a falha definitiva não muda o documento.
"""

from __future__ import annotations

import json
import logging
import os
import random
import socket
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.db import ProgrammingError, close_old_connections, connection, transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name
from opentelemetry import trace

from jobqueue.backoff import backoff_seconds
from jobqueue.dispatch import StepResult, run_step
from jobqueue.models import ProcessingJob

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)

ALL_STEPS: tuple[str, ...] = tuple(ProcessingJob.Step.values)
DEFAULT_HEARTBEAT_INTERVAL = 15.0
DEFAULT_SHUTDOWN_GRACE = 330.0
DEFAULT_ALIVE_FILE = Path("/tmp/worker-alive")
# Espera entre tentativas quando a tabela ainda não existe (worker subiu antes
# do initContainer `release` migrar o public).
MISSING_TABLE_WAIT = 10.0
UNDEFINED_TABLE_PGCODE = "42P01"

_ERROR_TYPE_MAX = 255
_STEPS_WITH_RUN = (ProcessingJob.Step.OCR, ProcessingJob.Step.EXTRACTION)


@dataclass(frozen=True)
class ClaimedJob:
    id: int
    tenant_schema: str
    document_id: uuid.UUID
    step: str
    attempts: int
    max_attempts: int
    orchestration_run_id: str
    triggered_by: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Outcome:
    """Destino do job depois de uma execução."""

    status: str  # done | queued | failed
    error_type: str = ""
    error_message: str = ""
    retry_in_seconds: float | None = None


class TenantNotFound(Exception):
    pass


def _table() -> str:
    return f'"{get_public_schema_name()}"."{ProcessingJob._meta.db_table}"'


def _is_missing_table(exc: BaseException) -> bool:
    cause = exc.__cause__ or exc
    return getattr(cause, "pgcode", None) == UNDEFINED_TABLE_PGCODE


def decide(
    job: ClaimedJob, result: StepResult, *, rng: random.Random | None = None
) -> Outcome:
    """Sucesso → done; transitório com tentativas sobrando → queued com
    backoff; permanente ou esgotado → failed."""
    if result.ok:
        return Outcome(status=ProcessingJob.Status.DONE)
    if result.retryable and job.attempts < job.max_attempts:
        return Outcome(
            status=ProcessingJob.Status.QUEUED,
            error_type=result.error_type,
            error_message=result.error_message,
            retry_in_seconds=backoff_seconds(job.attempts, rng=rng),
        )
    return Outcome(
        status=ProcessingJob.Status.FAILED,
        error_type=result.error_type,
        error_message=result.error_message,
    )


class Worker:
    def __init__(
        self,
        *,
        concurrency: int = 2,
        poll_interval: float = 2.0,
        steps: Iterable[str] = ALL_STEPS,
        shutdown_grace: float = DEFAULT_SHUTDOWN_GRACE,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        alive_file: Path | None = DEFAULT_ALIVE_FILE,
        stop_event: threading.Event | None = None,
        step_runner: Callable[[ClaimedJob, Any], StepResult] = run_step,
        rng: random.Random | None = None,
    ) -> None:
        steps = tuple(steps)
        unknown = set(steps) - set(ALL_STEPS)
        if unknown or not steps:
            raise ValueError(f"Etapas inválidas: {sorted(unknown) or steps}")
        if concurrency < 1:
            raise ValueError("concurrency deve ser >= 1")
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self.steps = steps
        self.shutdown_grace = shutdown_grace
        self.heartbeat_interval = heartbeat_interval
        self.alive_file = alive_file
        self.identity = f"{socket.gethostname()}:{os.getpid()}"
        self._stop = stop_event or threading.Event()
        self._heartbeat_stop = threading.Event()
        self._step_runner = step_runner
        self._rng = rng
        self._active: dict[int, str] = {}
        self._active_lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    # --- ciclo de vida ----------------------------------------------------

    def stop(self) -> None:
        """Para de fazer claims. Os jobs em curso terminam (até o prazo)."""
        self._stop.set()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    def active_job_ids(self) -> list[int]:
        with self._active_lock:
            return list(self._active)

    def run(self) -> int:
        logger.info(
            "jobqueue_worker_started | identity=%s | concurrency=%s | steps=%s | poll_interval=%s",
            self.identity,
            self.concurrency,
            ",".join(self.steps),
            self.poll_interval,
        )
        self._threads = [
            threading.Thread(
                target=self._worker_loop, name=f"jobqueue-worker-{i}", daemon=True
            )
            for i in range(1, self.concurrency + 1)
        ]
        heartbeat = threading.Thread(
            target=self._heartbeat_loop, name="jobqueue-heartbeat", daemon=True
        )
        for thread in self._threads:
            thread.start()
        heartbeat.start()

        # Espera com timeout, e não um wait() sem prazo, para os signal handlers
        # (que rodam na main thread) serem atendidos logo.
        while not self._stop.wait(1.0):
            pass

        logger.info(
            "jobqueue_worker_stopping | active_jobs=%s | grace_seconds=%s",
            self.active_job_ids(),
            self.shutdown_grace,
        )
        deadline = time.monotonic() + self.shutdown_grace
        for thread in self._threads:
            thread.join(max(0.0, deadline - time.monotonic()))

        leftover = self.active_job_ids()
        if leftover:
            # As threads são daemon: o processo sai mesmo assim. Os jobs ficam
            # `running` sem heartbeat e voltam pela recuperação (AR-34).
            logger.warning(
                "jobqueue_worker_grace_expired | unfinished_jobs=%s", leftover
            )
        self._heartbeat_stop.set()
        heartbeat.join(5.0)
        logger.info("jobqueue_worker_stopped | identity=%s", self.identity)
        return 0

    # --- threads ------------------------------------------------------------

    def _worker_loop(self) -> None:
        locked_by = f"{self.identity}:{threading.current_thread().name}"
        while not self._stop.is_set():
            job: ClaimedJob | None = None
            try:
                close_old_connections()
                job = self.claim_next(locked_by)
                if job is None:
                    self._stop.wait(self.poll_interval)
                    continue
                with self._active_lock:
                    self._active[job.id] = locked_by
                self.run_job(job, locked_by)
            except ProgrammingError as exc:
                if not _is_missing_table(exc):
                    logger.exception("jobqueue_worker_error | locked_by=%s", locked_by)
                    self._close_connection()
                    self._stop.wait(self.poll_interval)
                    continue
                logger.warning(
                    "jobqueue_table_missing | waiting %ss for migrations",
                    MISSING_TABLE_WAIT,
                )
                self._close_connection()
                self._stop.wait(MISSING_TABLE_WAIT)
            except Exception:
                logger.exception(
                    "jobqueue_worker_error | locked_by=%s | job_id=%s",
                    locked_by,
                    job.id if job else None,
                )
                self._close_connection()
                self._stop.wait(self.poll_interval)
            finally:
                if job is not None:
                    with self._active_lock:
                        self._active.pop(job.id, None)
                    self._close_connection()
        self._close_connection()

    def _heartbeat_loop(self) -> None:
        while True:
            self.heartbeat_tick()
            if self._heartbeat_stop.wait(self.heartbeat_interval):
                break
        self._close_connection()

    def heartbeat_tick(self) -> int:
        """Uma batida: atualiza os jobs deste processo e grava a liveness.
        Devolve quantos jobs foram atualizados."""
        updated = 0
        job_ids = self.active_job_ids()
        if job_ids:
            try:
                close_old_connections()
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        UPDATE {_table()}
                           SET heartbeat_at = now(), updated_at = now()
                         WHERE id = ANY(%s) AND status = 'running' AND locked_by LIKE %s
                        """,
                        [job_ids, f"{self.identity}:%"],
                    )
                    updated = cursor.rowcount
            except Exception:
                logger.exception("jobqueue_heartbeat_failed | job_ids=%s", job_ids)
                self._close_connection()
        self._write_alive_file()
        return updated

    def _write_alive_file(self) -> None:
        if self.alive_file is None:
            return
        if self._threads and not all(thread.is_alive() for thread in self._threads):
            logger.error("jobqueue_worker_thread_dead | liveness não atualizada")
            return
        try:
            self.alive_file.write_text(f"{time.time():.0f}\n")
        except OSError:
            logger.exception("jobqueue_alive_file_failed | path=%s", self.alive_file)

    @staticmethod
    def _close_connection() -> None:
        try:
            connection.close()
        except Exception:
            logger.exception("jobqueue_connection_close_failed")

    # --- claim, execução e finalização ---------------------------------------

    def claim_next(self, locked_by: str) -> ClaimedJob | None:
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE {_table()}
                   SET status = 'running',
                       attempts = attempts + 1,
                       locked_by = %s,
                       locked_at = now(),
                       heartbeat_at = now(),
                       updated_at = now(),
                       orchestration_run_id = CASE
                           WHEN orchestration_run_id = '' AND step = ANY(%s) THEN %s
                           ELSE orchestration_run_id
                       END
                 WHERE id = (
                       SELECT id FROM {_table()}
                        WHERE status = 'queued'
                          AND run_after <= %s
                          AND step = ANY(%s)
                          AND attempts < max_attempts
                        ORDER BY run_after, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                 )
                RETURNING id, tenant_schema, document_id, step, attempts, max_attempts,
                          orchestration_run_id, triggered_by, payload
                """,
                [
                    locked_by[:255],
                    list(_STEPS_WITH_RUN),
                    str(uuid.uuid4()),
                    # Relógio do Python, o mesmo do enqueue (run_after), e não o
                    # now() do Postgres, que numa transação é o horário do BEGIN.
                    timezone.now(),
                    list(self.steps),
                ],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        payload = row[8]
        if isinstance(payload, (str, bytes)):
            # O Django desliga a decodificação de jsonb do psycopg2: num cursor
            # cru, o payload chega como texto.
            payload = json.loads(payload)
        return ClaimedJob(
            id=row[0],
            tenant_schema=row[1],
            document_id=row[2]
            if isinstance(row[2], uuid.UUID)
            else uuid.UUID(str(row[2])),
            step=row[3],
            attempts=row[4],
            max_attempts=row[5],
            orchestration_run_id=row[6],
            triggered_by=row[7],
            payload=payload if isinstance(payload, dict) else {},
        )

    def run_job(self, job: ClaimedJob, locked_by: str) -> Outcome:
        with _tracer.start_as_current_span(
            f"jobqueue.{job.step}",
            attributes={
                "jobqueue.job_id": job.id,
                "jobqueue.step": job.step,
                "jobqueue.attempt": job.attempts,
                "jobqueue.tenant_schema": job.tenant_schema,
                "document.id": str(job.document_id),
            },
        ):
            try:
                tenant = self._load_tenant(job.tenant_schema)
            except TenantNotFound as exc:
                outcome = Outcome(
                    status=ProcessingJob.Status.FAILED,
                    error_type="TenantNotFound",
                    error_message=str(exc),
                )
                tenant = None
            else:
                connection.set_tenant(tenant)
                try:
                    result = self._step_runner(job, tenant)
                except Exception as exc:
                    # Erro fora do @task (banco, busca do documento, conector do
                    # ERP): conta como transitório. O erp_dispatch tem
                    # max_attempts=1, então vai para failed do mesmo jeito.
                    logger.exception(
                        "jobqueue_step_error | job_id=%s | step=%s | document_id=%s",
                        job.id,
                        job.step,
                        job.document_id,
                    )
                    result = StepResult(
                        ok=False,
                        retryable=True,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                outcome = decide(job, result, rng=self._rng)

            try:
                self._finalize(job, locked_by, outcome)
            finally:
                connection.set_schema_to_public()

        log = (
            logger.info
            if outcome.status == ProcessingJob.Status.DONE
            else logger.warning
        )
        log(
            "jobqueue_job_finished | job_id=%s | step=%s | document_id=%s | tenant=%s | "
            "attempt=%s/%s | status=%s | error_type=%s | retry_in=%s",
            job.id,
            job.step,
            job.document_id,
            job.tenant_schema,
            job.attempts,
            job.max_attempts,
            outcome.status,
            outcome.error_type,
            None
            if outcome.retry_in_seconds is None
            else round(outcome.retry_in_seconds),
        )
        return outcome

    @staticmethod
    def _load_tenant(schema_name: str) -> Any:
        from tenants.models import Tenant

        connection.set_schema_to_public()
        try:
            return Tenant.objects.get(schema_name=schema_name)
        except Tenant.DoesNotExist:
            raise TenantNotFound(
                f"Tenant com schema {schema_name!r} não existe"
            ) from None

    def _finalize(self, job: ClaimedJob, locked_by: str, outcome: Outcome) -> None:
        guard = "WHERE id = %s AND status = 'running' AND locked_by = %s"
        guard_params = [job.id, locked_by[:255]]
        error_type = outcome.error_type[:_ERROR_TYPE_MAX]

        with transaction.atomic():
            with connection.cursor() as cursor:
                if outcome.status == ProcessingJob.Status.DONE:
                    cursor.execute(
                        f"""
                        UPDATE {_table()}
                           SET status = 'done', finished_at = now(), updated_at = now()
                         {guard}
                        """,
                        guard_params,
                    )
                elif outcome.status == ProcessingJob.Status.QUEUED:
                    cursor.execute(
                        f"""
                        UPDATE {_table()}
                           SET status = 'queued',
                               run_after = %s,
                               locked_by = '', locked_at = NULL, heartbeat_at = NULL,
                               last_error_type = %s, last_error_message = %s,
                               updated_at = now()
                         {guard}
                        """,
                        [
                            timezone.now()
                            + timedelta(seconds=outcome.retry_in_seconds),
                            error_type,
                            outcome.error_message,
                            *guard_params,
                        ],
                    )
                else:
                    cursor.execute(
                        f"""
                        UPDATE {_table()}
                           SET status = 'failed', finished_at = now(),
                               last_error_type = %s, last_error_message = %s,
                               updated_at = now()
                         {guard}
                        """,
                        [error_type, outcome.error_message, *guard_params],
                    )
                finalized = cursor.rowcount == 1

            if not finalized:
                # A recuperação (AR-34) já devolveu o job à fila ou o marcou
                # como falho: não sobrescrever nem encadear.
                logger.warning(
                    "jobqueue_job_lock_lost | job_id=%s | locked_by=%s | outcome=%s",
                    job.id,
                    locked_by,
                    outcome.status,
                )
                return

            if (
                outcome.status == ProcessingJob.Status.DONE
                and job.step == ProcessingJob.Step.OCR
            ):
                # Mesma transação do `done`: o job de extração existe se, e só
                # se, o OCR ficou concluído.
                from jobqueue.services import enqueue

                enqueue(
                    job.document_id,
                    ProcessingJob.Step.EXTRACTION,
                    triggered_by=job.triggered_by,
                    orchestration_run_id=job.orchestration_run_id,
                    tenant_schema=job.tenant_schema,
                )
