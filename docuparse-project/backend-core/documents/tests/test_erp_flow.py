"""Fluxo do analista para lançar a despesa no ERP: aprovar, confirmar, falhar e reenviar.

Nenhum teste fala com o Superlógica: o conftest de `erp_export/tests` bloqueia HTTP
real, e as chamadas passam por sessões falsas.
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import requests
from condominiums.tests.base import TenantAPITestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from erp_export import payload
from erp_export.policy import LIVE_WRITES_ENV, SANDBOX_HOSTS_ENV
from erp_export.tests.conftest import block_real_http  # noqa: F401 (fixture autouse)
from erp_export.tests.helpers import (
    SANDBOX_HOST,
    SANDBOX_URL,
    SUPPLIER_CNPJ,
    FakeSession,
    boleto_fields,
    make_document,
    make_settings,
    make_world,
    save_fake_tokens,
)
from erp_export.tests.test_lookup import expense, reader
from erp_export.writer import SuperlogicaWriter
from events import validate_event
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import UserProfile
from users.models import Permission, Role

from documents.models import (
    Document,
    DocumentEvent,
    ERPIntegrationAttempt,
    IntegrationSettings,
    ValidationDecision,
)
from documents.services import erp_retry
from documents.services.erp_flow import prepare_after_approval
from documents.services.erp_retry import FINGERPRINT_KEY, STARTED_KEY
from documents.services.event_consumers import consume_erp_integration_requested

Mode = IntegrationSettings.SuperlogicaMode
Status = ERPIntegrationAttempt.Status
SUPPLIER_ROW = {
    payload.SUPPLIER_ID_KEY: "321",
    payload.SUPPLIER_TAX_ID_KEYS[0]: SUPPLIER_CNPJ,
}

SENDER_PERMISSIONS = ["inbox.view", "documents.validate", "erp.send"]


class ErpFlowTestCase(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        for code in SENDER_PERMISSIONS:
            Permission.objects.get_or_create(code=code, defaults={"description": code})
        self.tokens["sender"] = self._token("sender", SENDER_PERMISSIONS)
        self.authenticate("sender")

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(
            os.environ,
            {SANDBOX_HOSTS_ENV: SANDBOX_HOST, "DOCUPARSE_LOCAL_EVENT_DIR": tmp.name},
        )
        env.start()
        self.addCleanup(env.stop)
        events = self.settings(DOCUPARSE_LOCAL_EVENT_DIR=tmp.name)
        events.enable()
        self.addCleanup(events.disable)
        os.environ.pop(LIVE_WRITES_ENV, None)

        self.world = make_world()
        self.document = make_document(self.world, boleto_fields())
        self.read_session = FakeSession(
            {("GET", "fornecedores"): [SUPPLIER_ROW], ("GET", "despesas"): []}
        )
        self.write_session = FakeSession(
            {("POST", "despesas"): [{"id_despesa_des": "9001"}]}
        )
        self.dispatched: list[dict] = []

    # --- infraestrutura -------------------------------------------------

    def _token(self, role_name: str, permissions: list[str]) -> str:
        role, _ = Role.objects.get_or_create(name=role_name)
        role.permissions.set(Permission.objects.filter(code__in=permissions))
        user = self.user_model.objects.create_user(
            username=f"{role_name}@erp.test", password="pw"
        )
        UserProfile.objects.create(user=user, tenant=self.tenant, role_ref=role)
        token = RefreshToken.for_user(user)
        token["tenant"] = self.tenant.slug
        return str(token.access_token)

    @property
    def user_model(self):
        from django.contrib.auth import get_user_model

        return get_user_model()

    def use_mode(self, mode=Mode.SANDBOX, *, dry_run=False, base_url=SANDBOX_URL):
        config = make_settings(mode, dry_run=dry_run, base_url=base_url)
        save_fake_tokens(config)
        return config

    def run_inline(self):
        """Faz o disparo em segundo plano rodar na hora, com sessões falsas no lugar do ERP."""

        def inline(event):
            self.dispatched.append(event)
            consume_erp_integration_requested(event)

        patches = [
            patch(
                "documents.services.erp_publisher.submit_erp_dispatch",
                side_effect=inline,
            ),
            patch(
                "erp_export.connector.SuperlogicaClient",
                lambda app, acc, url: reader(self.read_session),
            ),
            patch(
                "erp_export.connector.SuperlogicaWriter",
                lambda app, acc, url: SuperlogicaWriter(
                    app, acc, url, session=self.write_session
                ),
            ),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def confirm(self, document=None):
        return self.client.post(
            reverse("document-erp-confirm", args=[(document or self.document).id])
        )

    def retry(self, document=None):
        return self.client.post(
            reverse("document-erp-retry", args=[(document or self.document).id])
        )

    def erp(self, document=None):
        return self.client.get(
            reverse("document-erp", args=[(document or self.document).id])
        ).json()

    def attempt(self) -> ERPIntegrationAttempt:
        return ERPIntegrationAttempt.objects.get(document=self.document)

    def reload(self) -> Document:
        return Document.objects.get(pk=self.document.pk)

    def events(self, event_type):
        return DocumentEvent.objects.filter(
            document=self.document, event_type=event_type
        )


class ApprovalGatingTests(ErpFlowTestCase):
    def test_disabled_keeps_the_existing_behavior(self):
        make_settings(Mode.DISABLED)
        self.run_inline()
        prepare_after_approval(self.document)
        assert self.attempt().status == Status.REQUESTED
        assert self.reload().status == Document.Status.ERP_INTEGRATION_REQUESTED
        assert self.dispatched == []  # nada é disparado no modo padrão

    def test_sandbox_waits_for_the_analyst_instead_of_sending(self):
        self.use_mode()
        self.run_inline()
        prepare_after_approval(self.document)
        assert self.attempt().status == Status.PENDING_CONFIRMATION
        assert self.reload().status == Document.Status.APPROVED
        assert self.dispatched == []
        assert self.write_session.calls == []

    def test_mock_still_integrates_on_approval_and_reaches_erp_sent(self):
        make_settings(Mode.MOCK)
        self.run_inline()
        prepare_after_approval(self.document)
        document = self.reload()
        assert document.status == Document.Status.ERP_SENT
        assert self.attempt().external_id.startswith("mock-")
        assert self.write_session.calls == [] and self.read_session.calls == []

    def test_approving_through_the_validation_endpoint_follows_the_mode(self):
        self.use_mode()
        self.run_inline()
        self.document.status = Document.Status.VALIDATION_PENDING
        self.document.save()
        response = self.client.post(
            reverse("document-validate", args=[self.document.id]),
            {"decision": ValidationDecision.Decision.APPROVED},
            format="json",
        )
        assert response.status_code == 201, response.content
        assert self.attempt().status == Status.PENDING_CONFIRMATION
        assert self.dispatched == []


class ConfirmTests(ErpFlowTestCase):
    def setUp(self):
        super().setUp()
        self.use_mode()
        self.run_inline()
        prepare_after_approval(self.document)

    def test_confirming_sends_and_records_who_and_when(self):
        response = self.confirm()
        assert response.status_code == 202, response.content
        assert self.reload().status == Document.Status.ERP_SENT
        attempt = self.attempt()
        assert attempt.status == Status.SENT
        assert attempt.external_id == "9001"
        assert len(self.write_session.posts()) == 1

        recorded = self.events("erp.send.confirmed").get()
        assert recorded.payload["data"]["confirmed_by"] == "sender@erp.test"
        assert recorded.occurred_at is not None
        validate_event(recorded.payload)  # respeita o contrato

    def test_a_confirmed_send_is_visible_in_the_document_detail_and_the_dashboard(self):
        self.confirm()
        detail = self.client.get(
            reverse("document-detail", args=[self.document.id])
        ).json()
        assert detail["erp"]["state"] == "sent"
        assert detail["erp"]["external_id"] == "9001"
        rows = self.client.get(reverse("processes-dashboard")).json()["results"]
        assert {row["id"]: row["erp_state"] for row in rows}[
            str(self.document.id)
        ] == "sent"

    def test_dry_run_confirmation_sends_nothing_and_leaves_the_document_approved(self):
        self.use_mode(dry_run=True)
        response = self.confirm()
        assert response.status_code == 202
        assert self.reload().status == Document.Status.APPROVED
        assert self.attempt().status == Status.DRY_RUN
        assert self.write_session.calls == [] and self.read_session.calls == []
        dry = self.events("erp.dry_run").get()
        assert dry.payload["data"]["preview"]["amount"] == "1000.00"
        validate_event(dry.payload)
        assert self.erp()["state"] == "dry_run"

    def test_confirming_twice_never_posts_twice(self):
        self.confirm()
        again = self.confirm()
        assert again.status_code == 409
        assert again.json()["code"] == "already_sent"
        assert len(self.write_session.posts()) == 1

    def test_user_without_the_permission_cannot_confirm_or_retry(self):
        self.authenticate("reviewer")  # documents.validate, mas sem erp.send
        assert self.confirm().status_code == 403
        assert self.retry().status_code == 403
        assert self.attempt().status == Status.PENDING_CONFIRMATION
        assert self.write_session.calls == []

    def test_the_status_endpoint_only_needs_to_view(self):
        self.authenticate("operator")  # só inbox.view
        assert (
            self.client.get(
                reverse("document-erp", args=[self.document.id])
            ).status_code
            == 200
        )

    def test_the_status_tells_the_screen_whether_this_user_can_send(self):
        assert self.erp()["can_send"] is True  # sender tem erp.send
        self.authenticate("reviewer")  # documents.validate, sem erp.send
        assert self.erp()["can_send"] is False
        self.authenticate("operator")
        assert self.erp()["can_send"] is False

    def test_the_embedded_detail_has_no_per_user_flag(self):
        detail = self.client.get(
            reverse("document-detail", args=[self.document.id])
        ).json()
        assert "can_send" not in detail["erp"]

    def test_invalid_document_is_refused_with_every_problem_and_nothing_is_sent(self):
        fields = self.document.extraction_result.fields
        fields["valor_boleto"] = {"value": "", "confidence": 1}
        fields["data_vencimento"] = {"value": "", "confidence": 1}
        self.document.extraction_result.fields = fields
        self.document.extraction_result.save()
        response = self.confirm()
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "invalid"
        assert {e["code"] for e in body["errors"]} == {
            "amount_missing",
            "due_date_missing",
        }
        assert self.dispatched == []
        assert self.events("erp.send.confirmed").count() == 0

    def test_the_status_shows_why_the_document_is_blocked(self):
        self.document.condominium = None
        self.document.save()
        body = self.erp()
        assert body["state"] == "blocked"
        assert body["can_confirm"] is False
        assert body["errors"][0]["code"] == "condominium_missing"

    def test_a_document_that_is_not_approved_cannot_be_sent(self):
        self.document.status = Document.Status.VALIDATION_PENDING
        self.document.save()
        response = self.confirm()
        assert response.status_code == 409
        assert response.json()["code"] == "not_approved"

    def test_confirmation_does_not_apply_in_mock_mode(self):
        make_settings(Mode.MOCK)
        response = self.confirm()
        assert response.status_code == 409
        assert response.json()["code"] == "not_required"

    def test_the_summary_before_confirming_shows_what_will_be_launched(self):
        body = self.erp()
        assert body["state"] == "awaiting_confirmation"
        assert body["can_confirm"] is True
        summary = body["summary"]
        assert summary["condominium"] == "Edifício Exemplo"
        assert summary["supplier"] == "Fornecedor Exemplo LTDA"
        assert summary["account"].startswith("2.1.02")
        assert summary["amount"] == "1000.00"
        assert summary["installments"] == [
            {"due_date": "2026-07-20", "amount": "1000.00"}
        ]


class FailureAndRetryTests(ErpFlowTestCase):
    def setUp(self):
        super().setUp()
        self.use_mode()
        self.run_inline()
        prepare_after_approval(self.document)

    def fail_with_a_timeout(self):
        self.write_session.routes[("POST", "despesas")] = requests.ReadTimeout(
            "sem resposta"
        )
        assert self.confirm().status_code == 202

    def test_a_network_failure_is_recorded_as_retryable_with_a_wait(self):
        self.fail_with_a_timeout()
        assert self.reload().status == Document.Status.ERP_FAILED
        attempt = self.attempt()
        assert attempt.status == Status.FAILED
        assert attempt.retry_count == 1
        assert attempt.next_retry_at > timezone.now()
        body = self.erp()
        assert body["state"] == "failed"
        assert body["code"] == "network_error"
        assert body["retryable"] is True
        assert body["can_retry"] is False  # ainda dentro da espera
        assert body["next_retry_at"]
        assert "pode ou não ter sido aceito" in body["reason"]

    def test_retry_is_refused_before_the_wait_is_over_and_nothing_is_sent(self):
        self.fail_with_a_timeout()
        posts_before = len(self.write_session.posts())
        response = self.retry()
        assert response.status_code == 409
        assert response.json()["code"] == "wait"
        assert len(self.write_session.posts()) == posts_before

    def test_retry_after_the_wait_reconciles_instead_of_duplicating(self):
        self.fail_with_a_timeout()
        ERPIntegrationAttempt.objects.filter(pk=self.attempt().pk).update(
            next_retry_at=timezone.now() - timedelta(seconds=1)
        )
        # O ERP aceitou o envio anterior; só a resposta se perdeu.
        self.read_session.routes[("GET", "despesas")] = [
            expense("777", due="20/07/2026")
        ]
        posts_before = len(self.write_session.posts())

        response = self.retry()
        assert response.status_code == 202, response.content
        assert self.reload().status == Document.Status.ERP_SENT
        assert self.attempt().external_id == "777"
        assert len(self.write_session.posts()) == posts_before  # nenhuma despesa nova
        retried = self.events("erp.send.retried").get()
        assert retried.payload["data"]["confirmed_by"] == "sender@erp.test"
        validate_event(retried.payload)

    def test_the_failure_keeps_the_marker_and_fingerprint_for_the_next_try(self):
        self.fail_with_a_timeout()
        payload = self.attempt().response_payload
        assert STARTED_KEY in payload and payload[FINGERPRINT_KEY]

    def test_correcting_the_document_after_a_lost_response_is_caught_end_to_end(self):
        self.fail_with_a_timeout()
        fields = self.document.extraction_result.fields
        fields["valor_boleto"] = {"value": "1200,00", "confidence": 1.0}
        self.document.extraction_result.fields = fields
        self.document.extraction_result.save()
        ERPIntegrationAttempt.objects.filter(pk=self.attempt().pk).update(
            next_retry_at=timezone.now() - timedelta(seconds=1)
        )
        posts_before = len(self.write_session.posts())

        assert self.retry().status_code == 202
        body = self.erp()
        assert body["code"] == "changed_after_unknown_send"
        assert body["retryable"] is False
        assert len(self.write_session.posts()) == posts_before

    def test_the_wait_grows_with_each_failure_and_attempts_run_out(self):
        waits = [erp_retry.next_retry_at(n, now=timezone.now()) for n in range(1, 6)]
        assert waits[4] is None  # esgotou na quinta
        spans = [(w - timezone.now()).total_seconds() for w in waits[:4]]
        assert spans == sorted(spans) and spans[0] < spans[3]

    def test_exhausted_attempts_cannot_be_retried(self):
        self.fail_with_a_timeout()
        ERPIntegrationAttempt.objects.filter(pk=self.attempt().pk).update(
            retry_count=erp_retry.MAX_ATTEMPTS, next_retry_at=None
        )
        response = self.retry()
        assert response.status_code == 409
        assert response.json()["code"] == "exhausted"
        assert self.erp()["exhausted"] is True

    def test_a_final_failure_asks_for_a_correction_and_cannot_be_retried(self):
        self.read_session.routes[
            ("GET", "fornecedores")
        ] = []  # fornecedor sem cadastro
        assert self.confirm().status_code == 202
        body = self.erp()
        assert body["state"] == "failed"
        assert body["code"] == "supplier_not_found"
        assert body["retryable"] is False
        assert "Cadastre o fornecedor" in body["reason"]
        response = self.retry()
        assert response.status_code == 409
        assert response.json()["code"] == "not_retryable"
        assert self.write_session.posts() == []

    def test_after_correcting_a_final_failure_the_analyst_confirms_again(self):
        self.read_session.routes[("GET", "fornecedores")] = []
        self.confirm()
        self.read_session.routes[("GET", "fornecedores")] = [
            SUPPLIER_ROW
        ]  # cadastrado no ERP
        assert self.erp()["can_confirm"] is True
        assert self.confirm().status_code == 202
        assert self.reload().status == Document.Status.ERP_SENT

    def test_a_retryable_failure_must_use_the_retry_not_the_confirmation(self):
        self.fail_with_a_timeout()
        response = self.confirm()
        assert response.status_code == 409
        assert response.json()["code"] == "use_retry"

    def test_expense_already_in_the_erp_is_reported_not_duplicated(self):
        self.read_session.routes[("GET", "despesas")] = [
            expense("555", due="20/07/2026")
        ]
        self.confirm()
        body = self.erp()
        assert body["code"] == "duplicate_in_erp"
        assert "555" in body["reason"]
        assert self.write_session.posts() == []


class SettingsApiTests(ErpFlowTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate("tenantAdmin")  # models.edit
        self.url = reverse("integration-settings")

    def test_dry_run_is_editable_and_defaults_to_on(self):
        assert self.client.get(self.url).json()["superlogica_dry_run"] is True
        response = self.client.patch(
            self.url, {"superlogica_dry_run": False}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["superlogica_dry_run"] is False

    def test_live_enabled_cannot_be_changed_through_the_api(self):
        response = self.client.patch(
            self.url, {"superlogica_live_enabled": True}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["superlogica_live_enabled"] is False

    def test_live_mode_is_refused_until_the_tenant_is_enabled(self):
        response = self.client.patch(
            self.url, {"superlogica_mode": "live"}, format="json"
        )
        assert response.status_code == 400
        assert IntegrationSettings.objects.get().superlogica_mode != Mode.LIVE


class LiveWritesCommandTests(ErpFlowTestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("erp_live_writes", *args, stdout=out)
        return out.getvalue()

    def config(self):
        connection.set_tenant(self.tenant)
        return IntegrationSettings.objects.get()

    def test_enabling_needs_the_tenant_slug_typed_back(self):
        make_settings(Mode.SANDBOX)
        with self.assertRaises(CommandError):
            self.run_command("--tenant", self.tenant.slug, "--enable")
        with self.assertRaises(CommandError):
            self.run_command(
                "--tenant", self.tenant.slug, "--enable", "--confirm", "outro"
            )
        assert self.config().superlogica_live_enabled is False

    def test_enable_then_disable(self):
        make_settings(Mode.SANDBOX)
        output = self.run_command(
            "--tenant", self.tenant.slug, "--enable", "--confirm", self.tenant.slug
        )
        assert "SUPERLOGICA_LIVE_WRITES" in output  # avisa das demais travas
        assert self.config().superlogica_live_enabled is True
        self.run_command("--tenant", self.tenant.slug, "--disable")
        assert self.config().superlogica_live_enabled is False

    def test_unknown_tenant(self):
        with self.assertRaises(CommandError):
            self.run_command("--tenant", "nao-existe", "--disable")


class ConsumerIdempotencyTests(ErpFlowTestCase):
    def test_processing_the_same_request_event_twice_sends_only_once(self):
        self.use_mode()
        self.run_inline()
        prepare_after_approval(self.document)
        assert self.confirm().status_code == 202
        assert len(self.dispatched) == 1

        # O mesmo evento chega de novo (reentrega do barramento).
        again = consume_erp_integration_requested(self.dispatched[0])
        assert again is None
        assert len(self.write_session.posts()) == 1
        assert (
            DocumentEvent.objects.filter(
                document=self.document, event_type="erp.integration.requested"
            ).count()
            == 1
        )
