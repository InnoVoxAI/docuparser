from __future__ import annotations

import uuid
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from jobqueue.models import ProcessingJob
from jobqueue.policy import STEP_POLICIES, policy_for

TABLE = ProcessingJob._meta.db_table
Step = ProcessingJob.Step
Status = ProcessingJob.Status


def _job(**overrides) -> ProcessingJob:
    fields = {
        "tenant_schema": "tenant_acme",
        "document_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "step": Step.OCR,
        "max_attempts": 5,
    }
    fields.update(overrides)
    return ProcessingJob.objects.create(**fields)


class ActiveJobConstraintTests(TestCase):
    """Um único job ativo (queued/running) por (tenant, documento, etapa)."""

    def test_second_active_job_for_same_step_is_rejected(self) -> None:
        for first, second in [
            (Status.QUEUED, Status.QUEUED),
            (Status.QUEUED, Status.RUNNING),
            (Status.RUNNING, Status.QUEUED),
        ]:
            with self.subTest(first=first, second=second):
                with transaction.atomic():
                    _job(status=first)
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        _job(status=second)
                    transaction.set_rollback(True)

    def test_finished_job_does_not_block_a_new_active_one(self) -> None:
        for finished in (Status.DONE, Status.FAILED, Status.CANCELLED):
            with self.subTest(finished=finished):
                with transaction.atomic():
                    _job(status=finished)
                    _job(status=Status.QUEUED)
                    transaction.set_rollback(True)

    def test_many_finished_jobs_for_same_step_are_allowed(self) -> None:
        _job(status=Status.FAILED)
        _job(status=Status.FAILED)
        _job(status=Status.DONE)
        assert ProcessingJob.objects.count() == 3

    def test_other_step_tenant_or_document_is_independent(self) -> None:
        _job()
        _job(step=Step.EXTRACTION)
        _job(tenant_schema="tenant_other")
        _job(document_id=uuid.uuid4())
        assert ProcessingJob.objects.filter(status=Status.QUEUED).count() == 4


class DatabaseCheckConstraintTests(TestCase):
    """O worker escreve por SQL cru: o banco precisa rejeitar valores inválidos."""

    def test_unknown_step_is_rejected(self) -> None:
        with self.assertRaises(IntegrityError):
            _job(step="layout")

    def test_unknown_status_is_rejected(self) -> None:
        with self.assertRaises(IntegrityError):
            _job(status="QUEUED")

    def test_attempts_cannot_exceed_max_attempts(self) -> None:
        _job(attempts=1, max_attempts=1)
        with self.assertRaises(IntegrityError):
            _job(step=Step.ERP_DISPATCH, attempts=2, max_attempts=1)

    def test_max_attempts_has_no_default(self) -> None:
        with self.assertRaises(IntegrityError):
            _job(max_attempts=None)


class JobDefaultsTests(TestCase):
    def test_new_job_is_queued_and_ready_to_run(self) -> None:
        job = _job()
        assert job.status == Status.QUEUED
        assert job.attempts == 0
        assert job.run_after is not None
        assert job.payload == {}
        assert job.locked_by == ""
        assert job.heartbeat_at is None


class TestStepPolicy:
    def test_ocr_and_extraction_retry_five_times(self) -> None:
        assert policy_for(Step.OCR).max_attempts == 5
        assert policy_for(Step.EXTRACTION).max_attempts == 5

    def test_erp_dispatch_is_never_retried_automatically(self) -> None:
        assert policy_for(Step.ERP_DISPATCH).max_attempts == 1

    def test_every_step_has_a_policy(self) -> None:
        assert set(STEP_POLICIES) == set(Step.values)

    def test_unknown_step_raises(self) -> None:
        with pytest.raises(ValueError, match="layout"):
            policy_for("layout")


@pytest.mark.django_db
class TestMigrationState:
    def test_models_and_migrations_are_in_sync(self) -> None:
        call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())


def _table_exists(schema: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            [schema, TABLE],
        )
        return cursor.fetchone() is not None


@pytest.mark.tenant_db
@pytest.mark.django_db
class TestTenantSchema:
    """A fila é global: a tabela existe só em `public`, nunca no schema do tenant."""

    def test_table_exists_only_in_public(self) -> None:
        from tenants.models import Tenant

        # auto_create_schema roda migrate_schemas no schema novo, como em prod.
        # O teste roda numa transação: o rollback desfaz o CREATE SCHEMA.
        tenant = Tenant.objects.create(slug="jobq-probe", name="Jobq Probe")

        assert _table_exists("public")
        assert not _table_exists(tenant.schema_name)
        # Sanidade: o schema foi migrado (tem tabelas de TENANT_APPS).
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = 'documents_document'",
                [tenant.schema_name],
            )
            assert cursor.fetchone() is not None
