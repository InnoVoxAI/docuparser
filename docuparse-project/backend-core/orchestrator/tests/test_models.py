from __future__ import annotations

from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone
from tenants.models import Tenant

from orchestrator.models import OrchestrationRun, TaskExecution


class OrchestratorModelTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="tenant-orchestrator", name="Tenant Orchestrator")
        connection.set_tenant(self.tenant)

    def test_orchestration_run_create_and_query(self) -> None:
        run = OrchestrationRun.objects.create(
            run_id=str(uuid4()), name="document_processing", started_at=timezone.now()
        )

        fetched = OrchestrationRun.objects.get(run_id=run.run_id)
        assert fetched.status == OrchestrationRun.Status.RUNNING
        assert fetched.name == "document_processing"

    def test_run_id_must_be_unique(self) -> None:
        run_id = str(uuid4())
        OrchestrationRun.objects.create(
            run_id=run_id, name="document_processing", started_at=timezone.now()
        )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                OrchestrationRun.objects.create(
                    run_id=run_id, name="document_processing", started_at=timezone.now()
                )

    def test_task_execution_create_and_cascade_delete(self) -> None:
        run = OrchestrationRun.objects.create(
            run_id=str(uuid4()), name="document_processing", started_at=timezone.now()
        )
        task = TaskExecution.objects.create(
            orchestration_run=run,
            task_id=uuid4(),
            task_name="ocr",
            status=TaskExecution.Status.OK,
            attempt=1,
            duration_ms=120,
            payload={"document_id": "abc"},
        )

        assert run.task_executions.count() == 1
        assert TaskExecution.objects.get(id=task.id).task_name == "ocr"

        run.delete()
        assert not TaskExecution.objects.filter(id=task.id).exists()

    def test_task_execution_error_fields(self) -> None:
        run = OrchestrationRun.objects.create(
            run_id=str(uuid4()), name="document_processing", started_at=timezone.now()
        )
        task = TaskExecution.objects.create(
            orchestration_run=run,
            task_id=uuid4(),
            task_name="extraction",
            status=TaskExecution.Status.ERROR,
            attempt=3,
            duration_ms=500,
            error_type="ValueError",
            error_message="schema not found",
        )

        fetched = TaskExecution.objects.get(id=task.id)
        assert fetched.status == TaskExecution.Status.ERROR
        assert fetched.attempt == 3
        assert fetched.error_type == "ValueError"
