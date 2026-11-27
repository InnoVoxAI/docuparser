from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "DocuParse OCR Backend"
    assert data["version"] == "1.0.0"
    # Verifica se o endpoint /api/v1/process está listado (aceita POST /api/v1/process)
    assert any("/api/v1/process" in endpoint for endpoint in data["endpoints"].keys())


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "docuparse-ocr-backend"}


def test_list_engines_endpoint():
    response = client.get("/api/v1/engines")
    assert response.status_code == 200
    data = response.json()
    assert "engines" in data
    assert data["total_count"] == len(data["engines"])


def test_health_responds_while_process_blocks(monkeypatch):
    """O OCR é bloqueante (OpenRouter, Tesseract) e pode levar minutos. Ele precisa
    rodar fora do event loop, senão /health para e a liveness do k8s mata o pod."""
    import asyncio
    import threading

    import httpx
    from api.routes import document as document_routes

    started = threading.Event()
    release = threading.Event()
    released_in_time: list[bool] = []

    def slow_process_document(**kwargs):
        started.set()
        released_in_time.append(release.wait(3))
        raise RuntimeError("fim do teste")

    monkeypatch.setattr(document_routes, "process_document", slow_process_document)

    async def scenario() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://ocr") as c:
            work = asyncio.create_task(
                c.post(
                    "/api/v1/process",
                    files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
                )
            )
            for _ in range(300):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            health = await asyncio.wait_for(c.get("/health"), timeout=2)
            release.set()
            await work
            return health

    health = asyncio.run(scenario())

    assert health.status_code == 200
    assert released_in_time == [True]
