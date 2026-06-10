FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OCR and OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-container.txt .
RUN pip install --no-cache-dir -r requirements-container.txt

# The default container keeps only the engines used by the current routing:
# docling/PyMuPDF for digital PDFs, OpenRouter for scanned files, and
# Tesseract fallback. Paddle/EasyOCR/TrOCR remain optional for local profiles.

COPY . .

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]
