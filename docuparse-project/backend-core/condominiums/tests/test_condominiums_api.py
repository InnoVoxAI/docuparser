"""API de condomínios: permissões, CNPJ e isolamento entre tenants."""

from __future__ import annotations

from django.db import connection
from django.urls import reverse
from tenants.models import Tenant

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase


class CondominiumAPITests(TenantAPITestCase):
    def _create(self, **payload: object):
        return self.client.post(reverse("condominiums"), payload, format="json")

    def test_operator_can_list_but_not_write(self) -> None:
        Condominium.objects.create(name="Edifício Exemplo")
        self.authenticate("operator")
        listing = self.client.get(reverse("condominiums"))
        assert listing.status_code == 200
        assert [c["name"] for c in listing.json()] == ["Edifício Exemplo"]
        assert self._create(name="Outro").status_code == 403

    def test_cnpj_is_stored_without_punctuation(self) -> None:
        response = self._create(name="Edifício Exemplo", cnpj="11.222.333/0001-81")
        assert response.status_code == 201
        assert response.json()["cnpj"] == "11222333000181"

    def test_accepts_alphanumeric_cnpj(self) -> None:
        response = self._create(name="Edifício Novo", cnpj="12.abc.345/01de-35")
        assert response.status_code == 201
        assert response.json()["cnpj"] == "12ABC34501DE35"

    def test_rejects_cnpj_with_wrong_check_digits(self) -> None:
        response = self._create(name="Edifício Exemplo", cnpj="11.222.333/0001-82")
        assert response.status_code == 400
        assert "cnpj" in response.json()

    def test_rejects_duplicate_cnpj(self) -> None:
        assert self._create(name="A", cnpj="11222333000181").status_code == 201
        response = self._create(name="B", cnpj="11.222.333/0001-81")
        assert response.status_code == 400
        assert "cnpj" in response.json()

    def test_cnpj_is_optional(self) -> None:
        assert self._create(name="Sem CNPJ 1").status_code == 201
        assert self._create(name="Sem CNPJ 2", cnpj="").status_code == 201

    def test_patch_and_delete(self) -> None:
        condominium = Condominium.objects.create(name="Antigo")
        url = reverse("condominium-detail", args=[condominium.id])
        patch = self.client.patch(
            url, {"name": "Novo", "external_id": "42"}, format="json"
        )
        assert patch.status_code == 200
        assert patch.json()["name"] == "Novo"
        assert patch.json()["external_id"] == "42"
        assert self.client.delete(url).status_code == 204
        assert not Condominium.objects.filter(id=condominium.id).exists()

    def test_condominiums_are_isolated_per_tenant(self) -> None:
        assert self._create(name="Só do tenant A").status_code == 201
        connection.set_schema_to_public()
        other = Tenant.objects.create(slug="condosb", name="Outra administradora")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token_for(other, 'tenantAdmin')}"
        )
        response = self.client.get(reverse("condominiums"))
        assert response.status_code == 200
        assert response.json() == []
