"""API do cadastro de fornecedores e da natureza das contas."""

from __future__ import annotations

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from django.urls import reverse

from accounting.models import LedgerAccount, SupplierRule


class SupplierRuleAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.condominium = Condominium.objects.create(name="Edifício Exemplo")
        self.water = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.1.01", name="Água"
        )
        self.other = Condominium.objects.create(name="Outro Edifício")

    def _create(self, **payload: object):
        payload.setdefault("ledger_account_id", str(self.water.id))
        return self.client.post(
            reverse("supplier-rules", args=[self.condominium.id]),
            payload,
            format="json",
        )

    def test_operator_can_list_but_not_write(self) -> None:
        self.authenticate("operator")
        listing = self.client.get(reverse("supplier-rules", args=[self.condominium.id]))
        assert listing.status_code == 200
        assert self._create(supplier_tax_id="09769035000164").status_code == 403

    def test_accepts_formatted_cnpj_and_cpf(self) -> None:
        cnpj = self._create(supplier_tax_id="09.769.035/0001-64")
        assert cnpj.status_code == 201
        assert cnpj.json()["supplier_tax_id"] == "09769035000164"
        cpf = self._create(supplier_tax_id="529.982.247-25")
        assert cpf.status_code == 201
        assert cpf.json()["supplier_tax_id"] == "52998224725"

    def test_rejects_invalid_tax_id(self) -> None:
        response = self._create(supplier_tax_id="09.769.035/0001-65")
        assert response.status_code == 400
        assert "supplier_tax_id" in response.json()

    def test_account_must_belong_to_the_condominium(self) -> None:
        foreign = LedgerAccount.objects.create(
            condominium=self.other, code="2.1.01", name="Água"
        )
        response = self._create(
            supplier_tax_id="09769035000164", ledger_account_id=str(foreign.id)
        )
        assert response.status_code == 400
        assert "ledger_account_id" in response.json()

    def test_same_supplier_needs_distinct_keywords(self) -> None:
        assert self._create(supplier_tax_id="08078021000131").status_code == 201
        assert (
            self._create(supplier_tax_id="08078021000131", keyword="MEN").status_code
            == 201
        )
        duplicate = self._create(supplier_tax_id="08.078.021/0001-31", keyword="MEN")
        assert duplicate.status_code == 400
        assert "keyword" in duplicate.json()

    def test_patch_and_delete(self) -> None:
        rule = SupplierRule.objects.create(
            condominium=self.condominium,
            supplier_tax_id="09769035000164",
            ledger_account=self.water,
        )
        url = reverse("supplier-rule-detail", args=[self.condominium.id, rule.id])
        patch = self.client.patch(url, {"is_active": False}, format="json")
        assert patch.status_code == 200
        assert patch.json()["is_active"] is False
        assert self.client.delete(url).status_code == 204

    def test_account_used_by_a_rule_cannot_be_deleted(self) -> None:
        SupplierRule.objects.create(
            condominium=self.condominium,
            supplier_tax_id="09769035000164",
            ledger_account=self.water,
        )
        url = reverse(
            "ledger-account-detail", args=[self.condominium.id, self.water.id]
        )
        assert self.client.delete(url).status_code == 409


class LedgerAccountNatureAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.condominium = Condominium.objects.create(name="Edifício Exemplo")
        self.other = Condominium.objects.create(name="Outro Edifício")

    def _create(self, condominium: Condominium, code: str, nature: str):
        return self.client.post(
            reverse("ledger-accounts", args=[condominium.id]),
            {"code": code, "name": "Inss", "nature": nature},
            format="json",
        )

    def test_nature_is_unique_per_condominium(self) -> None:
        first = self._create(self.condominium, "2.4.01", "inss")
        assert first.status_code == 201
        assert first.json()["nature"] == "inss"
        duplicate = self._create(self.condominium, "2.4.02", "inss")
        assert duplicate.status_code == 400
        assert "nature" in duplicate.json()
        assert self._create(self.other, "2.4.01", "inss").status_code == 201

    def test_rejects_unknown_nature(self) -> None:
        response = self._create(self.condominium, "2.4.01", "energia")
        assert response.status_code == 400
        assert "nature" in response.json()
