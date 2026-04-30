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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Install TrOCR dependencies for handwritten document support
# Uncomment the lines below to enable TrOCR support (adds ~2GB to image)
# COPY requirements-dev.txt .
# RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]
