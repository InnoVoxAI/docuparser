from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_process_mock_pdf():
    # Simulate a PDF upload
    files = {'file': ('test.pdf', b'%PDF-1.4 mock content', 'application/pdf')}
    response = client.post("/process", files=files)
    assert response.status_code == 200
    json_data = response.json()
    assert "tools_used" in json_data
    assert "transcription" in json_data
    assert "fields" in json_data["transcription"]
    assert "field_validation" in json_data["transcription"]
    assert "final_score" in json_data["transcription"]


def test_process_mock_image():
    # Simulate an image upload
    files = {'file': ('test.png', b'mock image content', 'image/png')}
    response = client.post("/process", files=files)
    assert response.status_code == 200
    json_data = response.json()
    assert "detected_type" in json_data
    assert "transcription" in json_data
    assert "fields" in json_data["transcription"]
