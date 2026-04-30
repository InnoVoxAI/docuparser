# Backend OCR - DocuParse

FastAPI service responsible for document analysis and data extraction using multiple OCR engines with a layered architecture.

## Architecture

The backend follows a clean architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Layered Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│  api/           ← HTTP layer (FastAPI endpoints, schemas)          │
│  application/   ← Orchestration (use cases, workflow coordination) │
│  domain/        ← Business logic (classifier, engine resolver)     │
│  infrastructure/ ← External integrations (OCR engines, fallback)   │
│  shared/        ← Reusable utilities (preprocessing, validators)   │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **api/** | HTTP layer: endpoints, request/response models | `routes/document.py`, `schemas/ocr_schema.py` |
| **application/** | Orchestration: coordinates the processing flow | `process_document.py` |
| **domain/** | Business rules: classification, engine selection | `classifier.py`, `engine_resolver.py`, `field_extractor.py` |
| **infrastructure/** | External integrations: OCR engines, fallback logic | `engines/`, `fallback/` |
| **shared/** | Reusable utilities: preprocessing, validation | `preprocessing.py`, `validators.py` |

## Supported Engines

| Engine | Use Case | Features |
|--------|----------|----------|
| **DeepSeek OCR** | Complex/handwritten documents | LLM-powered extraction, high accuracy |
| **OpenRouter** | Flexible LLM integration | Multiple model support via OpenRouter API |
| **Tesseract** | Standard images | Mature OCR engine, good for clean text |
| **PaddleOCR** | Multi-language | Excellent for Chinese, Japanese, Korean |
| **EasyOCR** | General purpose | Good balance of speed and accuracy |
| **Docling** | Digital PDFs | Preserves document structure |
| **LlamaParse** | Complex layouts | Advanced layout parsing with LLM |

## Configuration

Environment variables (set in `.env` or your environment):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434/v1` | URL of local Ollama instance |
| `OLLAMA_MODEL` | `deepseek-r1` | Model to use for LLM-powered OCR |
| `OPENROUTER_API_KEY` | - | API key for OpenRouter (optional) |

## Running Locally

### Prerequisites

- Python 3.10+
- Virtual environment (venv or conda)

### Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Option 1: Direct run
uvicorn api.app:app --host 0.0.0.0 --port 8080 --reload

# Option 2: With PYTHONPATH
PYTHONPATH=/path/to/backend-ocr python -m uvicorn api.app:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
# Build and run with Docker Compose
cd docuparse-project
docker-compose up --build backend-ocr
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/process` | Process document with OCR |
| `GET` | `/api/v1/engines` | List available OCR engines |
| `GET` | `/health` | Health check |
| `GET` | `/` | API information |

### Request Example

```bash
curl -X POST http://localhost:8080/api/v1/process \
  -F "file=@document.pdf"
```

### Response Example

```json
{
  "document_type": "digital_pdf",
  "raw_text": "...",
  "fields": {
    "document_number": "123456",
    "date": "2024-01-15",
    "total": "R$ 1500,00"
  },
  "confidence": 0.95,
  "engine_used": "openrouter"
}
```

## Development

### Project Structure

```
backend-ocr/
├── api/                    # HTTP layer
│   ├── app.py             # FastAPI setup
│   ├── routes/            # Endpoints
│   │   └── document.py
│   └── schemas/           # Pydantic models
│       └── ocr_schema.py
├── application/            # Orchestration
│   └── process_document.py
├── domain/                 # Business logic
│   ├── classifier.py
│   ├── engine_resolver.py
│   └── field_extractor.py
├── infrastructure/         # External integrations
│   ├── engines/           # OCR engine adapters
│   │   ├── base_engine.py
│   │   ├── openrouter_engine.py
│   │   ├── tesseract_engine.py
│   │   └── ...
│   └── fallback/          # Fallback logic
│       └── fallback_handler.py
├── shared/                 # Utilities
│   ├── preprocessing.py
│   └── validators.py
├── tests/                  # Test suite
│   ├── test_main.py
│   └── ...
└── docs/                   # Documentation
    ├── architecture_prd.md
    └── ...
```

### Adding a New Engine

1. Create a new file in `infrastructure/engines/`
2. Implement `BaseOCREngine` abstract class
3. Register in `domain/engine_resolver.py`

```python
from infrastructure.engines.base_engine import BaseOCREngine

class MyNewEngine(BaseOCREngine):
    @property
    def name(self) -> str:
        return "my_new_engine"
    
    def process(self, file_bytes: bytes, metadata: dict) -> dict:
        # OCR implementation
        return {"raw_text": "...", "confidence": 0.95, ...}
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_main.py -v
```

## Migration Notes

### From Legacy Architecture

The backend was refactored from a monolithic structure to layered architecture:

| Legacy | New Location |
|--------|--------------|
| `agent/router.py` | Fragmented into `domain/` + `application/` |
| `agent/classifier.py` | `domain/classifier.py` |
| `engines/*.py` | `infrastructure/engines/*.py` |
| `utils/preprocessing.py` | `shared/preprocessing.py` |
| `utils/validate_fields.py` | `domain/field_extractor.py` + `shared/validators.py` |
| `utils/ocr_fallback.py` | `infrastructure/fallback/fallback_handler.py` |

## License

MIT
