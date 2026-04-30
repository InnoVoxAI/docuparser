from fastapi.testclient import TestClient
from api.app import app
import os
import json

# Set env var for local test (Mac host) instead of docker internal
os.environ["OLLAMA_HOST"] = "http://localhost:11434/v1"

client = TestClient(app)

file_path = "/Users/dirceusilva/Documents/development/src/OCR/docuparser/docs_teste/AnyScanner_12_09_2025.pdf"

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
    exit(1)

print(f"Testing with file: {file_path}")

with open(file_path, "rb") as f:
    response = client.post(
        "/api/v1/process",
        files={"file": ("AnyScanner_12_09_2025.pdf", f, "application/pdf")}
    )

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
else:
    print("Error content:")
    print(response.content)
