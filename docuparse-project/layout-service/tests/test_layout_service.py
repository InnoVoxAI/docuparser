from __future__ import annotations

from api.app import app
from domain.classifier import classify_layout
from fastapi.testclient import TestClient


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {
        "status": "healthy",
        "service": "docuparse-layout-service",
    }
    assert client.get("/ready").json() == {
        "status": "ready",
        "service": "docuparse-layout-service",
    }


def test_classify_layout_endpoint() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/classify-layout",
        json={
            "raw_text": "Banco do Brasil 001 boleto linha digitavel cedente vencimento",
            "document_type": "scanned_image",
        },
    )

    assert response.status_code == 200
    assert response.json()["layout"] == "boleto_bb"
    assert response.json()["confidence"] >= 0.7


def test_initial_layout_heuristics() -> None:
    fixtures = {
        "boleto_caixa": "Caixa Economica Federal 104 boleto linha digitavel cedente vencimento",
        "boleto_bb": "Banco do Brasil 001 boleto linha digitavel cedente vencimento",
        "boleto_bradesco": "Bradesco 237 boleto linha digitavel beneficiario vencimento",
        "boleto_generico": (
            "BANCO ITAU SA 341-7 34191.09990 21296.322932 83012.370009 7 "
            "12910000247555 LOCAL DE PAGAMENTO VENCIMENTO BENEFICIARIO: "
            "BAHIANA DISTRIBUIDORA DE GAS NOSSO NUMERO PAGADOR FICHA DE COMPENSACAO"
        ),
        "fatura_energia": "Energia eletrica kWh unidade consumidora consumo distribuidora vencimento",
        "fatura_condominio": "Condominio unidade rateio assembleia sindico vencimento boleto",
        "generic": "recibo simples sem layout conhecido",
    }

    for expected, raw_text in fixtures.items():
        assert classify_layout(raw_text).layout == expected


def test_identified_bank_wins_over_generic_boleto() -> None:
    raw_text = (
        "Banco do Brasil 001 34191.09990 21296.322932 83012.370009 7 12910000247555 "
        "Beneficiário Pagador Nosso número Vencimento Ficha de compensação"
    )

    assert classify_layout(raw_text).layout == "boleto_bb"
