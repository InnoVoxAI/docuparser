from fastapi.testclient import TestClient
from api.app import app

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
