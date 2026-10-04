"""API do plano de contas: hierarquia, unicidade de código e exclusão protegida."""

from __future__ import annotations

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from django.urls import reverse

from accounting.models import LedgerAccount


class LedgerAccountAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.condominium = Condominium.objects.create(name="Edifício Exemplo")
        self.other = Condominium.objects.create(name="Outro Edifício")

    def _create(self, code: str, name: str, parent=None, condominium=None):
        condominium = condominium or self.condominium
        payload = {"code": code, "name": name}
        if parent is not None:
            payload["parent_id"] = str(parent)
        return self.client.post(
            reverse("ledger-accounts", args=[condominium.id]), payload, format="json"
        )

    def _detail(self, account_id, condominium=None) -> str:
        condominium = condominium or self.condominium
        return reverse("ledger-account-detail", args=[condominium.id, account_id])

    def test_operator_can_list_but_not_write(self) -> None:
        self.authenticate("operator")
        assert (
            self.client.get(
                reverse("ledger-accounts", args=[self.condominium.id])
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
        assert leaf.json()["condominium_id"] == str(self.condominium.id)

        listing = self.client.get(
            reverse("ledger-accounts", args=[self.condominium.id])
        )
        assert [a["code"] for a in listing.json()] == ["2", "2.1", "2.1.02"]

    def test_code_is_unique_per_condominium(self) -> None:
        assert self._create("2.1.02", "Energia elétrica").status_code == 201
        duplicate = self._create("2.1.02", "Outra")
        assert duplicate.status_code == 400
        assert "code" in duplicate.json()
        other = self._create("2.1.02", "Energia elétrica", condominium=self.other)
        assert other.status_code == 201

    def test_parent_must_belong_to_same_condominium(self) -> None:
        foreign = LedgerAccount.objects.create(
            condominium=self.other, code="2", name="X"
        )
        response = self._create("2.1", "Serviços Básicos", parent=foreign.id)
        assert response.status_code == 400
        assert "parent_id" in response.json()

    def test_rejects_cycles(self) -> None:
        root = LedgerAccount.objects.create(
            condominium=self.condominium, code="2", name="A"
        )
        child = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.1", name="B", parent=root
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
        root = LedgerAccount.objects.create(
            condominium=self.condominium, code="2", name="A"
        )
        account = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.9", name="Solta"
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
        root = LedgerAccount.objects.create(
            condominium=self.condominium, code="2", name="A"
        )
        leaf = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.1", name="B", parent=root
        )
        assert self.client.delete(self._detail(root.id)).status_code == 409
        assert self.client.delete(self._detail(leaf.id)).status_code == 204
        assert self.client.delete(self._detail(root.id)).status_code == 204

    def test_account_is_scoped_to_its_condominium(self) -> None:
        account = LedgerAccount.objects.create(
            condominium=self.condominium, code="2", name="A"
        )
        response = self.client.get(self._detail(account.id, condominium=self.other))
        assert response.status_code == 404

    def test_condominium_with_accounts_cannot_be_deleted(self) -> None:
        LedgerAccount.objects.create(condominium=self.condominium, code="2", name="A")
        response = self.client.delete(
            reverse("condominium-detail", args=[self.condominium.id])
        )
        assert response.status_code == 409
        assert Condominium.objects.filter(id=self.condominium.id).exists()
