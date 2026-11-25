"""Sessão HTTP falsa e fábricas de dados para os testes de escrita no ERP."""

from __future__ import annotations

import json
from typing import Any

from accounting.models import ChartOfAccounts, DocumentClassification, LedgerAccount
from condominiums.models import Condominium
from cryptography.fernet import Fernet
from django.db import connection
from documents.models import (
    SETTINGS_SINGLETON_ID,
    Document,
    ExtractionResult,
    IntegrationSettings,
)
from tenants.models import Tenant

# CNPJs fictícios, mas com dígitos verificadores válidos.
SUPPLIER_CNPJ = "12345678000195"
OTHER_CNPJ = "98765432000198"
CONDOMINIUM_ERP_ID = "501"
CHART_ERP_ID = "77"
SANDBOX_HOST = "sandbox.erp.test"
SANDBOX_URL = f"https://{SANDBOX_HOST}/v2/condor"


class FakeResponse:
    def __init__(self, status_code: int = 200, body: Any = None) -> None:
        self.status_code = status_code
        self._body = body

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("sem corpo")
        return self._body


class FakeSession:
    """Responde por (método, caminho final) e registra cada chamada."""

    def __init__(self, routes: dict[tuple[str, str], Any] | None = None) -> None:
        self.headers: dict[str, str] = {}
        self.routes = routes or {}
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        path = url.rsplit("/", 1)[-1]
        self.calls.append({"method": method, "path": path, "url": url, **kwargs})
        handler = self.routes.get((method, path))
        if handler is None:
            raise AssertionError(f"Rota não prevista no teste: {method} {path}")
        if isinstance(handler, Exception):
            raise handler
        if callable(handler):
            return handler(**kwargs)
        if isinstance(handler, FakeResponse):
            return handler
        return FakeResponse(200, handler)

    def methods(self) -> list[str]:
        return [call["method"] for call in self.calls]

    def posts(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call["method"] == "POST"]


def make_tenant(slug: str = "tenant-erp") -> Tenant:
    tenant = Tenant.objects.create(slug=slug, name=slug)
    connection.set_tenant(tenant)
    return tenant


def make_settings(
    mode: str, *, dry_run: bool = True, base_url: str = "", live_enabled: bool = False
) -> IntegrationSettings:
    config, _ = IntegrationSettings.objects.update_or_create(
        id=SETTINGS_SINGLETON_ID,
        defaults={
            "superlogica_mode": mode,
            "superlogica_dry_run": dry_run,
            "superlogica_base_url": base_url,
            "superlogica_live_enabled": live_enabled,
            # Os testes não gravam o JSON de exportação no disco.
            "approved_export_enabled": False,
        },
    )
    return config


def save_fake_tokens(config: IntegrationSettings, monkeypatch=None) -> None:
    import os

    from erp_import.credentials import save_superlogica_tokens

    os.environ.setdefault("DOCUPARSE_SECRETS_KEY", Fernet.generate_key().decode())
    save_superlogica_tokens(config, "app-token-fake", "access-token-fake")
    config.save()


def make_world(*, linked: bool = True) -> dict[str, Any]:
    chart = ChartOfAccounts.objects.create(
        name="Plano", external_source="superlogica", external_id=CHART_ERP_ID
    )
    account = LedgerAccount.objects.create(
        chart=chart, code="2.1.02", name="Manutenção"
    )
    condominium = Condominium.objects.create(
        name="Edifício Exemplo",
        external_source="superlogica" if linked else "",
        external_id=CONDOMINIUM_ERP_ID if linked else "",
        chart_of_accounts=chart,
    )
    return {"chart": chart, "account": account, "condominium": condominium}


def make_document(
    world: dict[str, Any],
    fields: dict[str, Any],
    *,
    status: str = Document.Status.APPROVED,
    classified: bool = True,
    filename: str = "doc.pdf",
) -> Document:
    document = Document.objects.create(
        status=status,
        channel="manual",
        file_uri=f"s3://x/{filename}",
        original_filename=filename,
        condominium=world["condominium"],
    )
    ExtractionResult.objects.create(
        document=document,
        schema_id="x",
        schema_version="v1",
        fields={k: {"value": v, "confidence": 1.0} for k, v in fields.items()},
    )
    if classified:
        DocumentClassification.objects.create(
            document=document,
            ledger_account=world["account"],
            origin=DocumentClassification.Origin.MANUAL,
        )
    return document


def invoice_fields(**overrides: Any) -> dict[str, Any]:
    base = {
        "cnpj_fornecedor": SUPPLIER_CNPJ,
        "fornecedor_nome": "Fornecedor Exemplo LTDA",
        "valor_nota": "1000,00",
        "numero_nota": "123",
        "data_emissao": "01/07/2026",
        "descricao_servico": "Manutenção predial",
    }
    return {**base, **overrides}


def boleto_fields(**overrides: Any) -> dict[str, Any]:
    base = {
        "cnpj_cpf_beneficiario": SUPPLIER_CNPJ,
        "beneficiario_nome": "Fornecedor Exemplo LTDA",
        "valor_boleto": "1000,00",
        "data_vencimento": "2026-07-20",
        "numero_documento": "B-1",
    }
    return {**base, **overrides}


def as_json(value: Any) -> str:
    return json.dumps(value, default=str)
