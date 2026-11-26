"""API do plano de contas: hierarquia, unicidade de código e exclusão protegida."""

from __future__ import annotations

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from django.urls import reverse

from accounting.models import ChartOfAccounts, LedgerAccount


class LedgerAccountAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.chart = ChartOfAccounts.objects.create(name="Plano Exemplo")
        self.other = ChartOfAccounts.objects.create(name="Outro Plano")

    def _create(self, code: str, name: str, parent=None, chart=None):
        chart = chart or self.chart
        payload = {"code": code, "name": name}
        if parent is not None:
            payload["parent_id"] = str(parent)
        return self.client.post(
            reverse("ledger-accounts", args=[chart.id]), payload, format="json"
        )

    def _detail(self, account_id, chart=None) -> str:
        chart = chart or self.chart
        return reverse("ledger-account-detail", args=[chart.id, account_id])

    def test_operator_can_list_but_not_write(self) -> None:
        self.authenticate("operator")
        assert (
            self.client.get(
                reverse("ledger-accounts", args=[self.chart.id])
            ).status_code
            == 200
        )
        assert self._create("2", "Despesas").status_code == 403

    def test_creates_hierarchy_listed_by_code(self) -> None:
        root = self._create("2", "Despesas").json()
        group = self._create("2.1", "Serviços Básicos", parent=root["id"]).json()
        leaf = self._create("2.1.02", "Energia elétrica", parent=group["id"])
        assert leaf.status_code == 201
        assert leaf.json()["parent_id"] == group["id"]
        assert leaf.json()["chart_id"] == str(self.chart.id)

        listing = self.client.get(reverse("ledger-accounts", args=[self.chart.id]))
        assert [a["code"] for a in listing.json()] == ["2", "2.1", "2.1.02"]

    def test_code_is_unique_per_chart(self) -> None:
        assert self._create("2.1.02", "Energia elétrica").status_code == 201
        duplicate = self._create("2.1.02", "Outra")
        assert duplicate.status_code == 400
        assert "code" in duplicate.json()
        other = self._create("2.1.02", "Energia elétrica", chart=self.other)
        assert other.status_code == 201

    def test_parent_must_belong_to_same_chart(self) -> None:
        foreign = LedgerAccount.objects.create(chart=self.other, code="2", name="X")
        response = self._create("2.1", "Serviços Básicos", parent=foreign.id)
        assert response.status_code == 400
        assert "parent_id" in response.json()

    def test_rejects_cycles(self) -> None:
        root = LedgerAccount.objects.create(chart=self.chart, code="2", name="A")
        child = LedgerAccount.objects.create(
            chart=self.chart, code="2.1", name="B", parent=root
        )
        onto_child = self.client.patch(
            self._detail(root.id), {"parent_id": str(child.id)}, format="json"
        )
        assert onto_child.status_code == 400
        onto_self = self.client.patch(
            self._detail(root.id), {"parent_id": str(root.id)}, format="json"
        )
        assert onto_self.status_code == 400

    def test_patch_can_move_and_rename(self) -> None:
        root = LedgerAccount.objects.create(chart=self.chart, code="2", name="A")
        account = LedgerAccount.objects.create(
            chart=self.chart, code="2.9", name="Solta"
        )
        response = self.client.patch(
            self._detail(account.id),
            {"parent_id": str(root.id), "name": "Manutenção"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["parent_id"] == str(root.id)
        assert response.json()["name"] == "Manutenção"

    def test_delete_is_blocked_while_account_has_children(self) -> None:
        root = LedgerAccount.objects.create(chart=self.chart, code="2", name="A")
        leaf = LedgerAccount.objects.create(
            chart=self.chart, code="2.1", name="B", parent=root
        )
        assert self.client.delete(self._detail(root.id)).status_code == 409
        assert self.client.delete(self._detail(leaf.id)).status_code == 204
        assert self.client.delete(self._detail(root.id)).status_code == 204

    def test_account_is_scoped_to_its_chart(self) -> None:
        account = LedgerAccount.objects.create(chart=self.chart, code="2", name="A")
        response = self.client.get(self._detail(account.id, chart=self.other))
        assert response.status_code == 404

    def test_chart_with_accounts_cannot_be_deleted(self) -> None:
        LedgerAccount.objects.create(chart=self.chart, code="2", name="A")
        response = self.client.delete(
            reverse("chart-of-accounts-detail", args=[self.chart.id])
        )
        assert response.status_code == 409
        assert ChartOfAccounts.objects.filter(id=self.chart.id).exists()

    def test_condominium_route_lists_the_accounts_of_its_chart(self) -> None:
        LedgerAccount.objects.create(chart=self.chart, code="2", name="A")
        LedgerAccount.objects.create(chart=self.other, code="9", name="Fora")
        condominium = Condominium.objects.create(
            name="Edifício Exemplo", chart_of_accounts=self.chart
        )
        without_chart = Condominium.objects.create(name="Sem Plano")

        listing = self.client.get(
            reverse("condominium-ledger-accounts", args=[condominium.id])
        )
        assert [a["code"] for a in listing.json()] == ["2"]
        empty = self.client.get(
            reverse("condominium-ledger-accounts", args=[without_chart.id])
        )
        assert empty.status_code == 200
        assert empty.json() == []
