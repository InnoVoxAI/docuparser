# Architecture Overview

## Services

### 1. Frontend (React + Vite)
- **Role**: User Interface.
- **Port**: 3000.
- **Responsibilities**:
    - File upload UI.
    - Displaying extracted JSON data.
    - Auth pages (future).

### 2. Backend Core (Django)
- **Role**: API Gateway & Management.
- **Port**: 8000.
- **Responsibilities**:
    - Authentication & User Management.
    - Document storage tracking.
    - Proxies OCR requests to `backend-ocr`.

### 3. Backend OCR (FastAPI)
- **Role**: OCR Processing Engine.
- **Port**: 8080.
- **Responsibilities**:
    - Receives file.
    - Classifies file type (PDF/Image/Handwritten).
    - Routes to appropriate engine (Tesseract/EasyOCR/etc.).
    - Returns structured JSON.

## Data Flow
1. User uploads file via **Frontend**.
2. **Frontend** sends file to **Backend Core**.
3. **Backend Core** validates user/permissions and forwards file to **Backend OCR**.
4. **Backend OCR** processes and returns JSON to **Backend Core**.
5. **Backend Core** saves metadata and returns JSON to **Frontend**.
