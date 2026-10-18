"""API de importação: sincronizar, listar, decidir e credenciais."""

from __future__ import annotations

import os
from unittest import mock

from accounting.models import ChartOfAccounts, LedgerAccount
from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from cryptography.fernet import Fernet
from django.db import connection
from documents.models import SETTINGS_SINGLETON_ID, IntegrationSettings

from erp_import import services
from erp_import.credentials import KEY_ENV
from erp_import.models import ImportBatch, ImportProposal
from erp_import.sources.base import (
    SourceAccount,
    SourceChart,
    SourceCondominium,
    SourceError,
)

CNPJ = "11222333000181"


def condo(ext_id, name="Edificio A", cnpj=CNPJ, active=True, address="Rua 1, 10"):
    return SourceCondominium(
        str(ext_id), name, cnpj, False, active, "7", address, "", ""
    )


class FakeSource:
    source_name = "superlogica"

    def __init__(self, condos=None):
        self.condos = condos if condos is not None else [condo(1)]
        self.error = None

    def list_condominiums(self):
        if self.error:
            raise SourceError(self.error)
        return self.condos

    def list_charts(self):
        return [SourceChart("7", "Padrao")]

    def list_accounts(self, _chart_external_id):
        return [
            SourceAccount("2", "Despesas", "", False),
            SourceAccount("2.1", "Agua", "2", False),
        ]

    def check_connection(self):
        if self.error:
            raise SourceError(self.error)


class InlineExecutor:
    """Roda a sincronização na hora, na conexão do teste."""

    def submit(self, _fn, batch_pk, _tenant, source, administrator_cnpj):
        services.execute_batch(
            ImportBatch.objects.get(pk=batch_pk), source, administrator_cnpj
        )


class ImportApiTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.source = FakeSource()
        patches = [
            mock.patch(
                "erp_import.background.build_superlogica_source", lambda: self.source
            ),
            mock.patch("erp_import.background._executor", InlineExecutor()),
            mock.patch(
                "erp_import.views.build_superlogica_source", lambda: self.source
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def sync(self):
        return self.client.post("/api/ocr/import/sync")

    def pending(self, **params):
        response = self.client.get("/api/ocr/import/proposals", params)
        assert response.status_code == 200, response.content
        return response.json()["results"]

    def proposal(self, entity_type, external_id):
        return next(
            p
            for p in self.pending()
            if (p["entity_type"], p["external_id"]) == (entity_type, external_id)
        )

    def decide(self, proposal, decision, body=None):
        return self.client.post(
            f"/api/ocr/import/proposals/{proposal['id']}/{decision}",
            body or {},
            format="json",
        )

    def test_sync_creates_proposals_and_writes_nothing(self):
        response = self.sync()
        assert response.status_code == 202, response.content
        assert {(p["entity_type"], p["action"]) for p in self.pending()} == {
            ("chart", "new"),
            ("condominium", "new"),
        }
        assert Condominium.objects.count() == 0
        assert ChartOfAccounts.objects.count() == 0
        assert LedgerAccount.objects.count() == 0

        overview = self.client.get("/api/ocr/import/overview").json()
        assert overview["latest_batch"]["status"] == "ready"
        assert overview["pending_by_action"]["new"] == 2

    def test_sync_requires_edit_permission(self):
        self.authenticate("operator")
        assert self.sync().status_code == 403
        assert ImportBatch.objects.count() == 0

    def test_sync_without_credentials_says_why_and_calls_nothing(self):
        from erp_import.credentials import CredentialsError

        def missing():
            raise CredentialsError(
                "As credenciais do Superlógica não foram configuradas."
            )

        with mock.patch("erp_import.background.build_superlogica_source", missing):
            response = self.sync()
        assert response.status_code == 400
        assert "credenciais" in response.json()["detail"]
        assert ImportBatch.objects.count() == 0

    def test_source_failure_leaves_error_batch_without_proposals(self):
        self.source.error = "O Superlógica respondeu HTTP 500 em condominios/get."
        assert self.sync().status_code == 202
        batch = ImportBatch.objects.get()
        assert batch.status == "error" and "HTTP 500" in batch.error_message
        assert ImportProposal.objects.count() == 0

    def test_second_sync_while_running_is_refused(self):
        ImportBatch.objects.create(source="superlogica", status="running")
        assert self.sync().status_code == 409

    def test_approving_applies_atomically_and_is_idempotent(self):
        self.sync()
        chart = self.proposal("chart", "7")
        assert self.decide(chart, "approve").status_code == 200
        assert LedgerAccount.objects.filter(chart__external_id="7").count() == 2
        child = LedgerAccount.objects.get(code="2.1")
        assert child.parent.code == "2"

        again = self.decide(chart, "approve")
        assert again.status_code == 200
        assert ChartOfAccounts.objects.count() == 1
        assert LedgerAccount.objects.count() == 2

        assert (
            self.decide(self.proposal("condominium", "1"), "approve").status_code == 200
        )
        created = Condominium.objects.get(external_id="1")
        assert created.cnpj == CNPJ and created.chart_of_accounts.external_id == "7"
        assert created.external_source == "superlogica"

        decided = ImportProposal.objects.get(external_id="7", entity_type="chart")
        assert (
            decided.status == "approved"
            and decided.decided_by_id
            and decided.decided_at
        )

    def test_condominium_before_its_chart_is_refused_and_rolled_back(self):
        self.sync()
        response = self.decide(self.proposal("condominium", "1"), "approve")
        assert (
            response.status_code == 409
            and "plano de contas" in response.json()["detail"]
        )
        assert Condominium.objects.count() == 0
        assert ImportProposal.objects.get(entity_type="condominium").status == "pending"

    def test_bulk_approve_applies_charts_first_and_reports_failures(self):
        self.sync()
        ids = [p["id"] for p in self.pending()]
        response = self.client.post(
            "/api/ocr/import/proposals/approve", {"ids": ids}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["failed"] == []
        assert Condominium.objects.get(external_id="1").chart_of_accounts is not None

        response = self.client.post(
            "/api/ocr/import/proposals/approve",
            {"ids": [str(ImportProposal.objects.first().id)]},
            format="json",
        )
        assert response.status_code == 200  # already decided: idempotent

    def test_rejected_proposal_does_not_come_back_unchanged(self):
        self.sync()
        assert (
            self.decide(self.proposal("condominium", "1"), "reject").status_code == 200
        )
        self.sync()
        assert [p for p in self.pending() if p["entity_type"] == "condominium"] == []
        self.source.condos = [condo(1, name="Edificio A2")]
        self.sync()
        assert self.proposal("condominium", "1")["data"]["name"] == "Edificio A2"

    def test_updates_and_deactivation_after_import(self):
        self.sync()
        for p in self.pending():
            self.decide(p, "approve")
        self.source.condos = [condo(1, name="Renomeado")]
        self.sync()
        assert (
            self.decide(self.proposal("condominium", "1"), "approve").status_code == 200
        )
        assert Condominium.objects.get(external_id="1").name == "Renomeado"

        self.source.condos = []
        self.sync()
        proposal = self.proposal("condominium", "1")
        assert proposal["action"] == "deactivate"
        self.decide(proposal, "approve")
        assert Condominium.objects.get(external_id="1").is_active is False

    def test_cnpj_conflict_is_resolved_for_the_whole_group(self):
        self.source.condos = [
            condo(1, name="Edificio A", address="Rua 1"),
            condo(2, name="Edificio B", address="Rua 2"),
        ]
        self.sync()
        self.decide(self.proposal("chart", "7"), "approve")
        first = self.proposal("condominium", "1")
        assert first["action"] == "conflict" and first["data"]["cnpj"] == ""
        assert len(first["data"]["cnpj_candidates"]) == 2

        assert (
            self.decide(first, "approve").status_code == 409
        )  # conflicts are resolved, not approved
        assert (
            self.decide(
                first, "resolve", {"resolution": {"cnpj_owner": "999"}}
            ).status_code
            == 409
        )

        response = self.decide(first, "resolve", {"resolution": {"cnpj_owner": "2"}})
        assert response.status_code == 200 and len(response.json()) == 2
        assert Condominium.objects.get(external_id="2").cnpj == CNPJ
        assert Condominium.objects.get(external_id="1").cnpj == ""
        assert self.pending(entity_type="condominium") == []

    def test_leaving_the_cnpj_unassigned_is_remembered(self):
        self.source.condos = [
            condo(1, name="Edificio A", address="Rua 1"),
            condo(2, name="Edificio B", address="Rua 2"),
        ]
        self.sync()
        self.decide(self.proposal("chart", "7"), "approve")
        first = self.proposal("condominium", "1")
        self.decide(first, "resolve", {"resolution": {"cnpj_owner": None}})
        assert Condominium.objects.filter(cnpj=CNPJ).count() == 0

        self.sync()
        assert self.pending(entity_type="condominium") == []

        # A new record joining the group is a different situation and is asked again.
        self.source.condos.append(condo(3, name="Edificio C", address="Rua 3"))
        self.sync()
        assert {p["action"] for p in self.pending(entity_type="condominium")} == {
            "conflict"
        }

    def test_cnpj_held_by_a_local_record_can_be_linked(self):
        local = Condominium.objects.create(name="Cadastro local", cnpj=CNPJ)
        self.sync()
        self.decide(self.proposal("chart", "7"), "approve")
        conflict = self.proposal("condominium", "1")
        assert conflict["data"]["conflict_kind"] == "cnpj_taken_locally"
        self.decide(conflict, "resolve", {"resolution": {"link_to_local": True}})
        local.refresh_from_db()
        assert (local.external_source, local.external_id) == ("superlogica", "1")
        assert Condominium.objects.count() == 1

    def test_test_connection_reports_ok_and_failure(self):
        assert self.client.post("/api/ocr/import/test-connection").json()["ok"] is True
        self.source.error = "O Superlógica recusou as credenciais (HTTP 401)."
        body = self.client.post("/api/ocr/import/test-connection").json()
        assert body["ok"] is False and "401" in body["detail"]


class CredentialsApiTests(TenantAPITestCase):
    URL = "/api/ocr/settings/integrations"

    def setUp(self):
        super().setUp()
        patch = mock.patch.dict(os.environ, {KEY_ENV: Fernet.generate_key().decode()})
        patch.start()
        self.addCleanup(patch.stop)

    def test_tokens_are_write_only_and_stored_encrypted(self):
        response = self.client.patch(
            self.URL,
            {
                "superlogica_app_token": "APP-SECRET",
                "superlogica_access_token": "ACCESS-SECRET",
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["superlogica_credentials_configured"] is True
        assert "APP-SECRET" not in str(body) and "ACCESS-SECRET" not in str(body)
        assert [key for key in body if "token" in key] == []
        assert [key for key in self.client.get(self.URL).json() if "token" in key] == []

        stored = IntegrationSettings.objects.get(id=SETTINGS_SINGLETON_ID)
        assert stored.superlogica_app_token_enc not in ("", "APP-SECRET")
        assert "APP-SECRET" not in stored.superlogica_app_token_enc
        assert "ACCESS-SECRET" not in str(self.client.get(self.URL).json())

        from erp_import.credentials import load_superlogica_tokens

        assert tuple(load_superlogica_tokens()) == ("APP-SECRET", "ACCESS-SECRET")

    def test_tokens_must_come_together(self):
        response = self.client.patch(
            self.URL, {"superlogica_app_token": "x"}, format="json"
        )
        assert response.status_code == 400

    def test_missing_key_is_a_readable_error(self):
        with mock.patch.dict(os.environ, {KEY_ENV: ""}):
            response = self.client.patch(
                self.URL,
                {"superlogica_app_token": "a", "superlogica_access_token": "b"},
                format="json",
            )
        assert response.status_code == 400 and KEY_ENV in response.json()["detail"]

    def test_administrator_cnpj_is_validated_and_normalized(self):
        ok = self.client.patch(
            self.URL, {"administrator_cnpj": "11.222.333/0001-81"}, format="json"
        )
        assert ok.json()["administrator_cnpj"] == CNPJ
        bad = self.client.patch(self.URL, {"administrator_cnpj": "123"}, format="json")
        assert bad.status_code == 400

    def test_sync_without_saved_credentials_makes_no_call(self):
        with mock.patch(
            "erp_import.sources.superlogica.requests.Session.request"
        ) as request:
            response = self.client.post("/api/ocr/import/sync")
        assert response.status_code == 400
        request.assert_not_called()
        assert ImportBatch.objects.count() == 0
        connection.set_tenant(self.tenant)
