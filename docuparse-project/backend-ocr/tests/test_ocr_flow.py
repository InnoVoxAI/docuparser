from fastapi.testclient import TestClient
from main import app
from agent.classifier import classify_document

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_classify_document():
    assert classify_document("scan.jpg", b"") == "scanned_image"
    assert classify_document("handwritten_note.png",
                             b"") == "handwritten_complex"
    assert classify_document("invoice.pdf", b"") == "scanned_image"
    assert classify_document("unknown.xyz", b"") == "scanned_image"

# Note: Integration tests with DeepSeek require a running Ollama instance and are mocked here or manual.
