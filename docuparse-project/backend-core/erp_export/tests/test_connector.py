"""O conector respeita a política, não duplica e reconcilia respostas perdidas."""

from __future__ import annotations

import os
from unittest.mock import patch

import requests
from django.test import TestCase
from documents.models import ERPIntegrationAttempt, IntegrationSettings
from documents.services.erp_retry import FINGERPRINT_KEY, STARTED_KEY

from erp_export import payload
from erp_export.connector import execute
from erp_export.policy import LIVE_WRITES_ENV, SANDBOX_HOSTS_ENV
from erp_export.writer import SuperlogicaWriter

from .helpers import (
    SANDBOX_HOST,
    SANDBOX_URL,
    SUPPLIER_CNPJ,
    FakeResponse,
    FakeSession,
    boleto_fields,
    make_document,
    make_settings,
    make_tenant,
    make_world,
    save_fake_tokens,
)
from .test_lookup import expense, reader

Mode = IntegrationSettings.SuperlogicaMode
KEY = "tenant:doc:erp:v1"
SUPPLIER_ROW = {
    payload.SUPPLIER_ID_KEY: "321",
    payload.SUPPLIER_TAX_ID_KEYS[0]: SUPPLIER_CNPJ,
}


def forbidden(*args, **kwargs):
    raise AssertionError("o conector tocou a rede onde a política proíbe")


class ConnectorBase(TestCase):
    def setUp(self):
        make_tenant(f"tenant-conn-{self._testMethodName[-24:].replace('_', '-')}")
        env = patch.dict(os.environ, {SANDBOX_HOSTS_ENV: SANDBOX_HOST}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(LIVE_WRITES_ENV, None)
        self.world = make_world()
        self.document = make_document(self.world, boleto_fields())
        self.attempt = ERPIntegrationAttempt.objects.create(
            document=self.document, connector="superlogica", idempotency_key=KEY
        )

    def settings(self, mode=Mode.SANDBOX, *, dry_run=False, base_url=SANDBOX_URL, **kw):
        config = make_settings(mode, dry_run=dry_run, base_url=base_url, **kw)
        save_fake_tokens(config)
        return config

    def run_connector(self, *, get=None, post=None, document=None):
        """Roda o conector com sessões falsas. Devolve (resultado, leitura, escrita)."""
        read_session = FakeSession(
            get
            if get is not None
            else {("GET", "fornecedores"): [SUPPLIER_ROW], ("GET", "despesas"): []}
        )
        write_session = FakeSession(
            {
                ("POST", "despesas"): post
                if post is not None
                else [{"id_despesa_des": "9001"}]
            }
        )
        result = execute(
            (document or self.document).id,
            KEY,
            reader_factory=lambda tokens, url: reader(read_session),
            writer_factory=lambda tokens, url: SuperlogicaWriter(
                tokens.app_token, tokens.access_token, url, session=write_session
            ),
        )
        return result, read_session, write_session

    def run_without_network(self):
        return execute(
            self.document.id, KEY, reader_factory=forbidden, writer_factory=forbidden
        )

    def reload(self):
        self.attempt.refresh_from_db()
        return self.attempt


class PolicyIsHonoredTests(ConnectorBase):
    def test_disabled_does_nothing(self):
        make_settings(Mode.DISABLED)
        result = self.run_without_network()
        assert result.kind == "ignored"

    def test_mock_never_touches_the_network(self):
        make_settings(Mode.MOCK)
        assert self.run_without_network().kind == "mock"

    def test_dry_run_builds_and_validates_but_never_sends(self):
        self.settings(dry_run=True)
        result = self.run_without_network()
        assert result.kind == "dry_run"
        attempt = self.reload()
        assert attempt.status == ERPIntegrationAttempt.Status.DRY_RUN
        assert attempt.response_payload["dry_run"] is True
        assert attempt.response_payload["preview"]["amount"] == "1000.00"
        assert attempt.response_payload["preview"]["supplier_tax_id"] == SUPPLIER_CNPJ

    def test_dry_run_does_not_need_credentials(self):
        make_settings(Mode.SANDBOX, dry_run=True, base_url=SANDBOX_URL)  # sem tokens
        assert self.run_without_network().kind == "dry_run"

    def test_dry_run_still_rejects_an_invalid_document(self):
        self.settings(dry_run=True)
        self.document.condominium = None
        self.document.save()
        result = self.run_without_network()
        assert result.kind == "failed"
        assert result.error.code == "condominium_missing"

    def test_sandbox_with_an_unlisted_host_is_blocked_without_network(self):
        self.settings(base_url="https://nao-listado.test/v2/condor")
        result = self.run_without_network()
        assert result.kind == "failed"
        assert result.error.code == "mode_blocked"
        assert result.error.retryable is False

    def test_sandbox_pointing_at_production_is_blocked_without_network(self):
        self.settings(base_url="https://api.superlogica.net/v2/condor")
        with patch.dict(os.environ, {SANDBOX_HOSTS_ENV: "api.superlogica.net"}):
            result = self.run_without_network()
        assert result.error.code == "mode_blocked"

    def test_live_is_blocked_without_network_even_with_everything_switched_on(self):
        self.settings(Mode.LIVE, base_url="", live_enabled=True)
        with patch.dict(os.environ, {LIVE_WRITES_ENV: "1"}):
            result = self.run_without_network()
        assert result.kind == "failed"
        assert result.error.code == "mode_blocked"
        assert "contrato" in result.error.message


class ValidationTests(ConnectorBase):
    def test_invalid_document_fails_without_network_and_lists_every_problem(self):
        self.settings()
        fields = self.document.extraction_result.fields
        fields["valor_boleto"] = {"value": "", "confidence": 1}
        fields["data_vencimento"] = {"value": "", "confidence": 1}
        self.document.extraction_result.fields = fields
        self.document.extraction_result.save()
        result = self.run_without_network()
        assert result.kind == "failed"
        assert result.error.retryable is False
        assert {e["code"] for e in result.detail["errors"]} == {
            "amount_missing",
            "due_date_missing",
        }


class SendTests(ConnectorBase):
    def test_happy_path_posts_once_and_returns_the_erp_id(self):
        self.settings()
        result, read, write = self.run_connector()
        assert result.kind == "sent"
        assert result.external_id == "9001"
        assert result.reconciled is False
        assert set(read.methods()) == {"GET"}
        assert len(write.posts()) == 1
        body = write.posts()[0]["json"]
        assert body["ID_FORNECEDOR_FOR"] == "321"
        assert body["APROPRIACAO"][0]["VL_VALOR_APRO"] == "1000.00"
        assert body["PARCELAS"][0]["DT_VENCIMENTO_PDES"] == "07/20/2026"  # MM/DD/AAAA

    def test_the_started_marker_is_saved_before_the_post(self):
        self.settings()
        seen = {}

        def post(**kwargs):
            seen["marker"] = (
                STARTED_KEY
                in ERPIntegrationAttempt.objects.get(
                    idempotency_key=KEY
                ).response_payload
            )
            return FakeResponse(200, [{"id_despesa_des": "1"}])

        self.run_connector(post=post)
        assert seen["marker"] is True

    def test_supplier_not_registered_stops_before_posting(self):
        self.settings()
        result, _, write = self.run_connector(
            get={("GET", "fornecedores"): [], ("GET", "despesas"): []}
        )
        assert result.kind == "failed"
        assert result.error.code == "supplier_not_found"
        assert result.error.retryable is False
        assert write.posts() == []

    def test_expense_already_in_the_erp_is_not_launched_again(self):
        self.settings()
        get = {
            ("GET", "fornecedores"): [SUPPLIER_ROW],
            ("GET", "despesas"): [expense("555", due="20/07/2026")],
        }
        result, _, write = self.run_connector(get=get)
        assert result.kind == "failed"
        assert result.error.code == "duplicate_in_erp"
        assert "555" in result.error.message
        assert result.error.retryable is False
        assert write.posts() == []

    def test_a_rejection_by_the_erp_is_final_and_clears_the_marker(self):
        self.settings()
        result, _, write = self.run_connector(post=FakeResponse(422, {}))
        assert result.error.code == "erp_rejected"
        assert result.error.retryable is False
        assert STARTED_KEY not in self.reload().response_payload

    def test_missing_credentials_fail_without_touching_the_network(self):
        make_settings(Mode.SANDBOX, dry_run=False, base_url=SANDBOX_URL)  # sem tokens
        result = self.run_without_network()
        assert result.kind == "failed"
        assert result.error.code == "credentials_missing"

    def test_lookup_trouble_is_retryable_and_posts_nothing(self):
        self.settings()
        result, _, write = self.run_connector(
            get={("GET", "fornecedores"): FakeResponse(503, [])}
        )
        assert result.error.code == "erp_lookup_failed"
        assert result.error.retryable is True
        assert write.posts() == []

    def test_rejected_credentials_on_lookup_are_not_retryable(self):
        self.settings()
        result, _, write = self.run_connector(
            get={("GET", "fornecedores"): FakeResponse(401, [])}
        )
        assert result.error.code == "auth_rejected"
        assert result.error.retryable is False
        assert write.posts() == []


class LostResponseTests(ConnectorBase):
    """Resposta perdida depois de um envio aceito não pode virar duas despesas."""

    def first_attempt_loses_the_response(self):
        self.settings()
        result, _, write = self.run_connector(post=requests.ReadTimeout("sem resposta"))
        assert result.kind == "failed"
        assert result.error.outcome_unknown is True
        assert result.error.retryable is True
        assert len(write.posts()) == 1
        # O consumidor de `erp.failed` grava a falha preservando o marcador; aqui o
        # marcador já está no banco porque o conector o escreveu antes do POST.
        assert STARTED_KEY in self.reload().response_payload

    def test_retry_finds_the_expense_in_the_erp_and_does_not_post_again(self):
        self.first_attempt_loses_the_response()
        get = {
            ("GET", "fornecedores"): [SUPPLIER_ROW],
            ("GET", "despesas"): [expense("777", due="20/07/2026")],
        }
        result, _, write = self.run_connector(get=get)
        assert result.kind == "sent"
        assert result.reconciled is True
        assert result.external_id == "777"
        assert write.posts() == []

    def test_retry_posts_again_only_when_the_erp_really_does_not_have_it(self):
        self.first_attempt_loses_the_response()
        result, _, write = (
            self.run_connector()
        )  # ERP sem a despesa: o envio anterior falhou de fato
        assert result.kind == "sent"
        assert result.reconciled is False
        assert len(write.posts()) == 1

    def test_without_the_marker_an_existing_expense_is_a_duplicate_not_a_reconciliation(
        self,
    ):
        self.settings()
        get = {
            ("GET", "fornecedores"): [SUPPLIER_ROW],
            ("GET", "despesas"): [expense("888", due="20/07/2026")],
        }
        result, _, _ = self.run_connector(get=get)
        assert result.error.code == "duplicate_in_erp"

    def test_the_marker_saves_a_fingerprint_of_what_was_sent(self):
        self.first_attempt_loses_the_response()
        assert self.reload().response_payload[FINGERPRINT_KEY]

    def test_a_document_corrected_after_a_lost_response_does_not_post_a_second_expense(
        self,
    ):
        self.first_attempt_loses_the_response()
        # O analista corrige o valor. A consulta usa o valor novo e não acha a despesa
        # antiga, que o ERP pode ter aceito com o valor errado.
        fields = self.document.extraction_result.fields
        fields["valor_boleto"] = {"value": "1200,00", "confidence": 1.0}
        self.document.extraction_result.fields = fields
        self.document.extraction_result.save()

        result, _, write = self.run_connector()  # ERP sem despesa com os dados novos
        assert result.kind == "failed"
        assert result.error.code == "changed_after_unknown_send"
        assert result.error.retryable is False
        assert write.posts() == []
        assert STARTED_KEY not in self.reload().response_payload

    def test_after_checking_the_erp_the_analyst_can_send_the_corrected_document(self):
        self.first_attempt_loses_the_response()
        fields = self.document.extraction_result.fields
        fields["valor_boleto"] = {"value": "1200,00", "confidence": 1.0}
        self.document.extraction_result.fields = fields
        self.document.extraction_result.save()
        self.run_connector()  # recusado, com o aviso

        result, _, write = self.run_connector()  # depois de conferir no ERP
        assert result.kind == "sent"
        assert len(write.posts()) == 1
