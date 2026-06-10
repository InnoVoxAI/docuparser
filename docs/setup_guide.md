# Setup Guide

## Prerequisites
- Docker
- Docker Compose

## Quick Start

1. **Clone the repository**

2. **Environment Setup**
    - Copy `.env.example` to `.env` (if applicable, currently `.env` is generated).

3. **Build and Run**
   ```bash
   cd docuparse-project
   docker-compose up --build
   ```

4. **Access Services**
    - Frontend: http://localhost:3000
    - Backend Core: http://localhost:8000
    - Backend OCR: http://localhost:8080/docs (Swagger UI)

## Development
- **Backend OCR**: Changes to `backend-ocr/` trigger auto-reload via `uvicorn --reload`.
- **Frontend**: Vite HMR is enabled.
