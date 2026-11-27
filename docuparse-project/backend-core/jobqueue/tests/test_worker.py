"""Worker da fila durável (AR-32).

- Backoff e decisão: sem banco.
- Claim, execução, classificação do erro, encadeamento ocr → extraction,
  retomada do run e troca de schema: `TestCase` com tenants reais.
- Claim concorrente e parada (SIGTERM simulado): `TransactionTestCase`, porque
  cada thread precisa da própria conexão vendo os commits das outras.
- Loop com a tabela ausente: `SimpleTestCase`, com o banco substituído.
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

import pytest
from django.db import ProgrammingError, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone
from django_tenants.utils import get_public_schema_name
from documents.models import Document
from documents.services.service_errors import (
    PermanentServiceError,
    TransientServiceError,
)
from orchestrator.models import OrchestrationRun, TaskExecution
from tenants.models import Tenant

from jobqueue.backoff import BASE_DELAYS_SECONDS, backoff_seconds
from jobqueue.dispatch import StepResult
from jobqueue.models import ProcessingJob
from jobqueue.services import enqueue
from jobqueue.worker import ClaimedJob, Worker, decide

Step = ProcessingJob.Step
Status = ProcessingJob.Status
OCR_BODY = "documents.services.ocr_processor.process_document_ocr"
EXTRACT_BODY = "documents.services.ocr_processor.auto_extract_after_ocr"
ERP_CONSUMER = "documents.services.event_consumers.consume_erp_integration_requested"


class _MidRng:
    """uniform(a, b) devolve o meio: sem jitter, o backoff é o valor base."""

    def uniform(self, a: float, b: float) -> float:
        return (a + b) / 2


def _claimed(**overrides) -> ClaimedJob:
    fields = dict(
        id=1,
        tenant_schema="tenant_x",
        document_id=uuid.uuid4(),
        step=Step.OCR,
        attempts=1,
        max_attempts=5,
        orchestration_run_id="run-1",
        triggered_by="",
        payload={},
    )
    fields.update(overrides)
    return ClaimedJob(**fields)


def _raw_job(**overrides) -> ProcessingJob:
    fields = {
        "tenant_schema": "tenant_x",
        "document_id": uuid.uuid4(),
        "step": Step.OCR,
        "max_attempts": 5,
    }
    fields.update(overrides)
    return ProcessingJob.objects.create(**fields)


# --- backoff e decisão (sem banco) ---------------------------------------


class TestBackoff:
    def test_base_delays_without_jitter(self) -> None:
        rng = _MidRng()
        assert [backoff_seconds(n, rng=rng) for n in (1, 2, 3, 4)] == [
            30,
            120,
            480,
            1800,
        ]

    def test_caps_at_last_delay(self) -> None:
        assert backoff_seconds(9, rng=_MidRng()) == BASE_DELAYS_SECONDS[-1]

    def test_jitter_stays_within_twenty_percent(self) -> None:
        for attempts, base in zip((1, 2, 3, 4), BASE_DELAYS_SECONDS):
            for _ in range(200):
                assert base * 0.8 <= backoff_seconds(attempts) <= base * 1.2

    def test_rejects_zero_attempts(self) -> None:
        with pytest.raises(ValueError):
            backoff_seconds(0)


class TestDecide:
    def test_success_is_done(self) -> None:
        assert decide(_claimed(), StepResult.success()).status == Status.DONE

    def test_transient_with_attempts_left_is_requeued_with_backoff(self) -> None:
        outcome = decide(
            _claimed(attempts=2),
            StepResult(ok=False, retryable=True, error_type="T", error_message="503"),
            rng=_MidRng(),
        )
        assert outcome.status == Status.QUEUED
        assert outcome.retry_in_seconds == 120
        assert (outcome.error_type, outcome.error_message) == ("T", "503")

    def test_transient_on_last_attempt_fails(self) -> None:
        outcome = decide(
            _claimed(attempts=5, max_attempts=5),
            StepResult(ok=False, retryable=True, error_type="T"),
        )
        assert outcome.status == Status.FAILED
        assert outcome.retry_in_seconds is None

    def test_permanent_fails_on_first_attempt(self) -> None:
        outcome = decide(
            _claimed(attempts=1), StepResult(ok=False, retryable=False, error_type="P")
        )
        assert outcome.status == Status.FAILED

    def test_erp_dispatch_never_requeues(self) -> None:
        outcome = decide(
            _claimed(step=Step.ERP_DISPATCH, attempts=1, max_attempts=1),
            StepResult(ok=False, retryable=True),
        )
        assert outcome.status == Status.FAILED


class TestWorkerArguments:
    def test_rejects_unknown_step(self) -> None:
        with pytest.raises(ValueError):
            Worker(steps=["ocr", "nope"])

    def test_rejects_zero_concurrency(self) -> None:
        with pytest.raises(ValueError):
            Worker(concurrency=0)


# --- claim -----------------------------------------------------------------


class ClaimTests(TestCase):
    def setUp(self) -> None:
        self.worker = Worker(alive_file=None)

    def test_claims_oldest_ready_job_and_marks_it_running(self) -> None:
        now = timezone.now()
        newer = _raw_job(run_after=now - timedelta(seconds=10))
        older = _raw_job(run_after=now - timedelta(seconds=60))

        job = self.worker.claim_next("host:1:t")

        assert job.id == older.id
        older.refresh_from_db()
        assert older.status == Status.RUNNING
        assert older.attempts == 1
        assert older.locked_by == "host:1:t"
        assert older.locked_at is not None and older.heartbeat_at is not None
        newer.refresh_from_db()
        assert newer.status == Status.QUEUED

    def test_skips_jobs_scheduled_for_later(self) -> None:
        _raw_job(run_after=timezone.now() + timedelta(minutes=5))
        assert self.worker.claim_next("w") is None

    def test_skips_non_queued_jobs(self) -> None:
        for status in (Status.RUNNING, Status.DONE, Status.FAILED, Status.CANCELLED):
            _raw_job(status=status)
        assert self.worker.claim_next("w") is None

    def test_only_claims_configured_steps(self) -> None:
        _raw_job(step=Step.OCR)
        erp = _raw_job(step=Step.ERP_DISPATCH, max_attempts=1)
        worker = Worker(steps=[Step.ERP_DISPATCH], alive_file=None)

        job = worker.claim_next("w")

        assert job.id == erp.id
        assert worker.claim_next("w") is None

    def test_skips_job_without_attempts_left(self) -> None:
        # Não deveria existir, mas sem o filtro o claim violaria a CHECK
        # attempts <= max_attempts e o worker entraria em loop de erro.
        _raw_job(attempts=5, max_attempts=5)
        assert self.worker.claim_next("w") is None

    def test_assigns_run_id_to_ocr_and_keeps_existing_one(self) -> None:
        fresh = _raw_job(step=Step.OCR)
        chained = _raw_job(step=Step.EXTRACTION, orchestration_run_id="existing-run")

        first = self.worker.claim_next("w")
        second = self.worker.claim_next("w")

        by_id = {first.id: first, second.id: second}
        uuid.UUID(by_id[fresh.id].orchestration_run_id)  # um uuid válido
        assert by_id[chained.id].orchestration_run_id == "existing-run"

    def test_erp_dispatch_gets_no_run_id(self) -> None:
        _raw_job(step=Step.ERP_DISPATCH, max_attempts=1)
        assert self.worker.claim_next("w").orchestration_run_id == ""

    def test_returns_payload_and_document_id(self) -> None:
        document_id = uuid.uuid4()
        _raw_job(
            step=Step.ERP_DISPATCH,
            max_attempts=1,
            document_id=document_id,
            payload={"event": 1},
            triggered_by="alice",
        )
        job = self.worker.claim_next("w")
        assert job.document_id == document_id
        assert job.payload == {"event": 1}
        assert job.triggered_by == "alice"


# --- execução com tenant real ------------------------------------------------


class _TenantJobTestCase(TestCase):
    slug = "jq-worker"
    locked_by = "host:1:jobqueue-worker-1"

    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug=self.slug, name="JQ Worker")
        connection.set_tenant(self.tenant)
        self.document = self._document()
        connection.set_schema_to_public()
        self.worker = Worker(alive_file=None, rng=_MidRng())

    def _document(self) -> Document:
        return Document.objects.create(
            channel="manual",
            file_uri=f"local://documents/{self.slug}/doc/original",
            original_filename="fixture.pdf",
        )

    def _enqueue(self, step=Step.OCR, **kwargs) -> ProcessingJob:
        job, created = enqueue(
            self.document, step, tenant_schema=self.tenant.schema_name, **kwargs
        )
        assert created
        return job

    def _claim_and_run(self):
        job = self.worker.claim_next(self.locked_by)
        assert job is not None
        return job, self.worker.run_job(job, self.locked_by)

    def _in_tenant(self, fn):
        connection.set_tenant(self.tenant)
        try:
            return fn()
        finally:
            connection.set_schema_to_public()


class EnqueueTests(_TenantJobTestCase):
    def test_creates_queued_job_with_step_policy(self) -> None:
        job = self._enqueue(Step.ERP_DISPATCH, payload={"x": 1}, triggered_by="bob")
        assert job.status == Status.QUEUED
        assert job.max_attempts == 1
        assert job.payload == {"x": 1}
        assert job.triggered_by == "bob"
        assert job.tenant_schema == self.tenant.schema_name

    def test_second_enqueue_returns_the_active_job(self) -> None:
        first = self._enqueue()
        again, created = enqueue(
            self.document.id, Step.OCR, tenant_schema=self.tenant.schema_name
        )
        assert not created
        assert again.id == first.id
        assert ProcessingJob.objects.count() == 1

    def test_reads_tenant_from_connection(self) -> None:
        job, _ = self._in_tenant(lambda: enqueue(self.document, Step.OCR))
        assert job.tenant_schema == self.tenant.schema_name

    def test_refuses_public_schema(self) -> None:
        with pytest.raises(ValueError):
            enqueue(self.document, Step.OCR)


class ClassificationTests(_TenantJobTestCase):
    def test_transient_error_requeues_with_backoff(self) -> None:
        self._enqueue()
        before = timezone.now()
        with mock.patch(
            OCR_BODY,
            side_effect=TransientServiceError("backend-ocr", "x", status_code=503),
        ) as ocr:
            job, outcome = self._claim_and_run()

        assert ocr.call_count == 1  # max_attempts=1: o tenacity não repete
        assert outcome.status == Status.QUEUED
        row = ProcessingJob.objects.get(id=job.id)
        assert row.status == Status.QUEUED
        assert row.attempts == 1
        assert row.last_error_type == "TransientServiceError"
        assert "503" in row.last_error_message
        assert (
            row.locked_by == "" and row.locked_at is None and row.heartbeat_at is None
        )
        delay = (row.run_after - before).total_seconds()
        assert 29 <= delay <= 32

    def test_permanent_error_fails_after_one_attempt(self) -> None:
        self._enqueue()
        with mock.patch(
            OCR_BODY,
            side_effect=PermanentServiceError("backend-ocr", "x", status_code=400),
        ) as ocr:
            job, outcome = self._claim_and_run()

        assert ocr.call_count == 1
        row = ProcessingJob.objects.get(id=job.id)
        assert row.status == Status.FAILED
        assert row.attempts == 1
        assert row.finished_at is not None
        assert row.last_error_type == "PermanentServiceError"
        # Nada encadeado.
        assert not ProcessingJob.objects.filter(step=Step.EXTRACTION).exists()

    def test_transient_error_on_last_attempt_fails(self) -> None:
        queued = self._enqueue()
        ProcessingJob.objects.filter(id=queued.id).update(attempts=4)
        with mock.patch(
            OCR_BODY,
            side_effect=TransientServiceError("backend-ocr", "x", status_code=503),
        ):
            job, outcome = self._claim_and_run()

        assert job.attempts == 5
        assert ProcessingJob.objects.get(id=job.id).status == Status.FAILED

    def test_exception_outside_task_counts_as_transient(self) -> None:
        self._enqueue()

        def broken(job, tenant):
            raise RuntimeError("db hiccup")

        self.worker = Worker(alive_file=None, rng=_MidRng(), step_runner=broken)
        job, outcome = self._claim_and_run()

        row = ProcessingJob.objects.get(id=job.id)
        assert row.status == Status.QUEUED
        assert row.last_error_type == "RuntimeError"

    def test_unknown_tenant_fails_permanently(self) -> None:
        ghost = _raw_job(tenant_schema="tenant_ghost")
        job, outcome = self._claim_and_run()

        assert job.id == ghost.id
        row = ProcessingJob.objects.get(id=ghost.id)
        assert row.status == Status.FAILED
        assert row.last_error_type == "TenantNotFound"

    def test_lost_lock_is_not_overwritten_nor_chained(self) -> None:
        self._enqueue()
        job = self.worker.claim_next(self.locked_by)
        # Simula a recuperação (AR-34) devolvendo o job à fila no meio.
        ProcessingJob.objects.filter(id=job.id).update(
            status=Status.QUEUED, locked_by=""
        )
        with mock.patch(OCR_BODY, return_value=self.document):
            self.worker.run_job(job, self.locked_by)

        row = ProcessingJob.objects.get(id=job.id)
        assert row.status == Status.QUEUED
        assert not ProcessingJob.objects.filter(step=Step.EXTRACTION).exists()


class ChainingAndRunTests(_TenantJobTestCase):
    def _run_for(self, run_id: str) -> OrchestrationRun:
        return self._in_tenant(lambda: OrchestrationRun.objects.get(run_id=run_id))

    def _executions(self, run_id: str) -> list[tuple[str, str, int]]:
        return self._in_tenant(
            lambda: list(
                TaskExecution.objects.filter(orchestration_run__run_id=run_id)
                .order_by("created_at")
                .values_list("task_name", "status", "attempt")
            )
        )

    def test_ocr_success_enqueues_extraction_in_the_same_run(self) -> None:
        self._enqueue(triggered_by="alice")
        with mock.patch(OCR_BODY, return_value=self.document):
            ocr_job, outcome = self._claim_and_run()

        assert outcome.status == Status.DONE
        ocr_row = ProcessingJob.objects.get(id=ocr_job.id)
        assert ocr_row.status == Status.DONE and ocr_row.finished_at is not None

        extraction = ProcessingJob.objects.get(step=Step.EXTRACTION)
        assert extraction.status == Status.QUEUED
        assert extraction.tenant_schema == self.tenant.schema_name
        assert extraction.document_id == self.document.id
        assert extraction.orchestration_run_id == ocr_job.orchestration_run_id
        assert extraction.triggered_by == "alice"
        assert extraction.max_attempts == 5

        run = self._run_for(ocr_job.orchestration_run_id)
        assert run.name == "document_processing"
        assert run.status == OrchestrationRun.Status.COMPLETED
        assert run.document_id == self.document.id
        assert run.triggered_by == "alice"

        with mock.patch(EXTRACT_BODY) as extract:
            extraction_job, outcome = self._claim_and_run()

        assert extract.call_count == 1
        assert extraction_job.id == extraction.id
        assert outcome.status == Status.DONE
        # A extração não encadeia nada.
        assert ProcessingJob.objects.filter(status=Status.QUEUED).count() == 0

        run = self._run_for(ocr_job.orchestration_run_id)
        assert run.status == OrchestrationRun.Status.COMPLETED
        assert run.finished_at is not None
        assert self._executions(run.run_id) == [
            ("ocr", "OK", 1),
            ("extraction", "OK", 1),
        ]

    def test_retry_resumes_the_same_run_and_records_job_attempt(self) -> None:
        queued = self._enqueue()
        with mock.patch(
            OCR_BODY,
            side_effect=TransientServiceError("backend-ocr", "x", status_code=503),
        ):
            first, _ = self._claim_and_run()

        assert self._run_for(first.orchestration_run_id).status == "FAILED"

        ProcessingJob.objects.filter(id=queued.id).update(run_after=timezone.now())
        with mock.patch(OCR_BODY, return_value=self.document):
            second, outcome = self._claim_and_run()

        assert second.id == first.id
        assert second.attempts == 2
        assert second.orchestration_run_id == first.orchestration_run_id
        assert outcome.status == Status.DONE
        assert self._run_for(first.orchestration_run_id).status == "COMPLETED"
        assert self._executions(first.orchestration_run_id) == [
            ("ocr", "ERROR", 1),
            ("ocr", "OK", 2),
        ]

    def test_erp_dispatch_calls_consumer_with_payload_and_has_no_run(self) -> None:
        self._enqueue(
            Step.ERP_DISPATCH, payload={"event_type": "erp.integration.requested"}
        )
        with mock.patch(ERP_CONSUMER) as consumer:
            job, outcome = self._claim_and_run()

        consumer.assert_called_once_with({"event_type": "erp.integration.requested"})
        assert outcome.status == Status.DONE
        assert job.orchestration_run_id == ""
        assert ProcessingJob.objects.filter(status=Status.QUEUED).count() == 0

    def test_erp_dispatch_failure_is_never_requeued(self) -> None:
        self._enqueue(Step.ERP_DISPATCH, payload={})
        with mock.patch(ERP_CONSUMER, side_effect=ConnectionError("superlogica")):
            job, outcome = self._claim_and_run()

        row = ProcessingJob.objects.get(id=job.id)
        assert row.status == Status.FAILED
        assert row.attempts == 1
        assert row.last_error_type == "ConnectionError"


class SchemaSwitchTests(_TenantJobTestCase):
    def test_job_runs_in_its_own_tenant_schema(self) -> None:
        other = Tenant.objects.create(slug="jq-other", name="JQ Other")
        connection.set_tenant(other)
        other_doc = Document.objects.create(
            channel="manual",
            file_uri="local://documents/jq-other/doc/original",
            original_filename="other.pdf",
        )
        connection.set_schema_to_public()
        self._enqueue(Step.EXTRACTION, orchestration_run_id=str(uuid.uuid4()))

        seen = {}

        def spy(job, tenant):
            seen["schema"] = connection.schema_name
            seen["tenant"] = tenant.slug
            seen["own"] = Document.objects.filter(id=job.document_id).exists()
            seen["other"] = Document.objects.filter(id=other_doc.id).exists()
            return StepResult.success()

        self.worker = Worker(alive_file=None, step_runner=spy)
        self._claim_and_run()

        assert seen == {
            "schema": self.tenant.schema_name,
            "tenant": self.slug,
            "own": True,
            "other": False,
        }
        # Volta ao public depois do job.
        assert connection.schema_name == get_public_schema_name()


class HeartbeatTests(TestCase):
    def test_tick_updates_only_this_process_jobs_and_writes_alive_file(self) -> None:
        with TemporaryDirectory() as tmp:
            alive = Path(tmp) / "worker-alive"
            worker = Worker(alive_file=alive)
            mine = _raw_job()
            theirs = _raw_job(step=Step.EXTRACTION)
            old = timezone.now() - timedelta(minutes=5)
            ProcessingJob.objects.filter(id=mine.id).update(
                status=Status.RUNNING,
                locked_by=f"{worker.identity}:t1",
                heartbeat_at=old,
            )
            ProcessingJob.objects.filter(id=theirs.id).update(
                status=Status.RUNNING, locked_by="other-host:9:t1", heartbeat_at=old
            )
            worker._active = {mine.id: "x", theirs.id: "x"}

            # Dentro do TestCase (autocommit desligado), close_old_connections
            # fecharia a conexão do teste.
            with mock.patch("jobqueue.worker.close_old_connections"):
                assert worker.heartbeat_tick() == 1

            mine.refresh_from_db()
            theirs.refresh_from_db()
            assert mine.heartbeat_at > old
            assert theirs.heartbeat_at == old
            assert alive.read_text().strip().isdigit()

    def test_alive_file_not_written_when_a_worker_thread_died(self) -> None:
        with TemporaryDirectory() as tmp:
            alive = Path(tmp) / "worker-alive"
            worker = Worker(alive_file=alive)
            dead = threading.Thread(target=lambda: None)
            dead.start()
            dead.join()
            worker._threads = [dead]

            worker.heartbeat_tick()

            assert not alive.exists()


# --- loop: tabela ausente (sem banco) -----------------------------------------


class MissingTableLoopTests(SimpleTestCase):
    def test_missing_table_logs_and_waits_instead_of_crashing(self) -> None:
        undefined = Exception("relation does not exist")
        undefined.pgcode = "42P01"
        error = ProgrammingError("relation does not exist")
        error.__cause__ = undefined

        worker = Worker(alive_file=None, poll_interval=0.01)
        calls = []

        def claim(locked_by):
            calls.append(locked_by)
            if len(calls) == 2:
                worker.stop()
                return None
            raise error

        with (
            mock.patch.object(worker, "claim_next", side_effect=claim),
            mock.patch("jobqueue.worker.close_old_connections"),
            mock.patch.object(Worker, "_close_connection"),
            mock.patch("jobqueue.worker.MISSING_TABLE_WAIT", 0.01),
            self.assertLogs("jobqueue.worker", level="WARNING") as logs,
        ):
            worker._worker_loop()

        assert len(calls) == 2
        assert any("jobqueue_table_missing" in line for line in logs.output)

    def test_other_errors_are_logged_with_traceback_and_loop_continues(self) -> None:
        worker = Worker(alive_file=None, poll_interval=0.01)
        calls = []

        def claim(locked_by):
            calls.append(locked_by)
            if len(calls) == 3:
                worker.stop()
                return None
            raise RuntimeError("connection reset")

        with (
            mock.patch.object(worker, "claim_next", side_effect=claim),
            mock.patch("jobqueue.worker.close_old_connections"),
            mock.patch.object(Worker, "_close_connection") as close,
            self.assertLogs("jobqueue.worker", level="ERROR") as logs,
        ):
            worker._worker_loop()

        assert len(calls) == 3
        assert close.call_count >= 2
        errors = [r for r in logs.records if "jobqueue_worker_error" in r.getMessage()]
        assert errors and all(r.exc_info for r in errors)
        assert sum("jobqueue_worker_error" in line for line in logs.output) == 2


# --- concorrência e parada (conexões reais por thread) ---------------------------


class _PublicTenantWorker(Worker):
    """Sem tenant real: o TransactionTestCase só limpa as tabelas do jobqueue."""

    @staticmethod
    def _load_tenant(schema_name):
        return SimpleNamespace(schema_name=get_public_schema_name(), slug="public")


def _in_thread(fn, results, key):
    def target():
        try:
            results[key] = fn()
        except Exception as exc:  # pragma: no cover - aparece no assert
            results[key] = exc
        finally:
            connection.close()

    thread = threading.Thread(target=target)
    thread.start()
    return thread


class ConcurrentClaimTests(TransactionTestCase):
    available_apps = ["jobqueue"]

    def test_locked_job_is_skipped_by_a_second_connection(self) -> None:
        from django.db import transaction

        first = _raw_job(run_after=timezone.now() - timedelta(seconds=60))
        second = _raw_job(run_after=timezone.now() - timedelta(seconds=30))
        worker = Worker(alive_file=None)
        holding = threading.Event()
        release = threading.Event()
        results: dict = {}

        def hold_first():
            with transaction.atomic():
                job = worker.claim_next("A")
                holding.set()
                release.wait(10)
                return job.id

        thread_a = _in_thread(hold_first, results, "a")
        assert holding.wait(10)
        thread_b = _in_thread(lambda: worker.claim_next("B").id, results, "b")
        thread_b.join(10)
        release.set()
        thread_a.join(10)

        assert results == {"a": first.id, "b": second.id}

    def test_many_threads_never_claim_the_same_job(self) -> None:
        jobs = [_raw_job() for _ in range(30)]
        worker = Worker(alive_file=None)
        results: dict = {}

        def drain(name):
            claimed = []
            while (job := worker.claim_next(name)) is not None:
                claimed.append(job.id)
            return claimed

        threads = [_in_thread(lambda n=n: drain(f"w{n}"), results, n) for n in range(4)]
        for thread in threads:
            thread.join(30)

        claimed = [job_id for ids in results.values() for job_id in ids]
        assert sorted(claimed) == sorted(job.id for job in jobs)
        assert len(set(claimed)) == len(claimed)


class ShutdownTests(TransactionTestCase):
    available_apps = ["jobqueue"]

    def _blocking_worker(self, *, grace: float):
        started = threading.Event()
        release = threading.Event()

        def step(job, tenant):
            started.set()
            release.wait(10)
            return StepResult.success()

        worker = _PublicTenantWorker(
            concurrency=1,
            poll_interval=0.05,
            heartbeat_interval=0.05,
            shutdown_grace=grace,
            alive_file=None,
            step_runner=step,
        )
        return worker, started, release

    def _run_in_background(self, worker):
        results: dict = {}
        thread = threading.Thread(target=lambda: results.setdefault("rc", worker.run()))
        thread.start()
        return thread, results

    def test_stop_finishes_the_running_job_and_claims_nothing_else(self) -> None:
        running = _raw_job(step=Step.EXTRACTION, orchestration_run_id="r")
        worker, started, release = self._blocking_worker(grace=10)
        thread, results = self._run_in_background(worker)
        assert started.wait(10)

        worker.stop()  # o que o handler de SIGTERM faz
        waiting = _raw_job(step=Step.EXTRACTION, orchestration_run_id="r2")
        release.set()
        thread.join(15)

        assert not thread.is_alive()
        assert results["rc"] == 0
        assert ProcessingJob.objects.get(id=running.id).status == Status.DONE
        waiting.refresh_from_db()
        assert waiting.status == Status.QUEUED
        assert waiting.attempts == 0

    def test_grace_expiry_leaves_job_running_and_exits_zero(self) -> None:
        stuck = _raw_job(step=Step.EXTRACTION, orchestration_run_id="r")
        worker, started, release = self._blocking_worker(grace=0.2)
        thread, results = self._run_in_background(worker)
        assert started.wait(10)

        started_at = time.monotonic()
        with self.assertLogs("jobqueue.worker", level="WARNING") as logs:
            worker.stop()
            thread.join(10)
        assert time.monotonic() - started_at < 5
        assert results["rc"] == 0
        assert ProcessingJob.objects.get(id=stuck.id).status == Status.RUNNING
        assert any("jobqueue_worker_grace_expired" in line for line in logs.output)

        # Deixa a thread daemon terminar antes do flush do TransactionTestCase.
        release.set()
        for worker_thread in worker._threads:
            worker_thread.join(10)
