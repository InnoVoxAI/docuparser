from __future__ import annotations

from api import app as app_module
from api.app import app
from domain.schemas import ExtractedDocument
from fastapi.testclient import TestClient

BOLETO_TEXT = (
    "Beneficiario: ACME LTDA Vencimento 10/05/2026 Valor R$ 123,45 "
    "Linha digitavel 12345.12345 12345.123456 12345.123456 1 12345678901234"
)
BOLETO_SCHEMA = {
    "schema_id": "boleto_default",
    "version": "v1",
    "fields": [{"name": "valor_boleto", "type": "decimal"}],
}


def _fake_llm(raw_text, schema_definition, **kwargs) -> ExtractedDocument:
    return ExtractedDocument(
        schema_id=schema_definition["schema_id"],
        schema_version=schema_definition["version"],
        fields={"valor_boleto": {"value": "123.45", "confidence": 0.9}},
        confidence=0.9,
        requires_human_validation=False,
    )


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {
        "status": "healthy",
        "service": "docuparse-langextract-service",
    }
    assert client.get("/ready").json() == {
        "status": "ready",
        "service": "docuparse-langextract-service",
    }


def test_extract_endpoint_uses_schema_definition(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "extract_with_llm", _fake_llm)
    client = TestClient(app)

    response = client.post(
        "/api/v1/extract",
        json={
            "raw_text": BOLETO_TEXT,
            "layout": "boleto_bb",
            "document_type": "scanned_image",
            "schema_definition": BOLETO_SCHEMA,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["schema_id"] == "boleto_default"
    assert data["fields"]["valor_boleto"]["value"] == "123.45"


def test_extract_endpoint_requires_schema_definition() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/extract", json={"raw_text": BOLETO_TEXT})

    assert response.status_code == 422


def test_health_responds_while_extraction_blocks(monkeypatch) -> None:
    """A extração chama o LLM de forma bloqueante. Ela precisa rodar fora do event
    loop, senão /health para e a liveness do k8s mata o pod no meio da chamada."""
    import asyncio
    import threading

    import httpx

    started = threading.Event()
    release = threading.Event()
    released_in_time: list[bool] = []

    def slow_llm(raw_text, schema_definition, **kwargs) -> ExtractedDocument:
        started.set()
        released_in_time.append(release.wait(3))
        return _fake_llm(raw_text, schema_definition, **kwargs)

    monkeypatch.setattr(app_module, "extract_with_llm", slow_llm)

    async def scenario() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://le") as c:
            work = asyncio.create_task(
                c.post(
                    "/api/v1/extract",
                    json={
                        "raw_text": BOLETO_TEXT,
                        "schema_definition": BOLETO_SCHEMA,
                        "metadata": {},
                    },
                )
            )
            for _ in range(300):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            health = await asyncio.wait_for(c.get("/health"), timeout=2)
            release.set()
            assert (await work).status_code == 200
            return health

    health = asyncio.run(scenario())

    assert health.status_code == 200
    assert released_in_time == [True]
