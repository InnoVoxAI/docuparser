from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "docuparse-ocr-backend"}


def test_list_engines():
    response = client.get("/api/v1/engines")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["engines"], list)
    assert data["total_count"] == len(data["engines"])

# Note: Integration tests with DeepSeek require a running Ollama instance and are mocked here or manual.
