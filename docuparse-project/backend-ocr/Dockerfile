FROM python:3.13-slim

# Static uv/uvx binaries — avoids a `pip install uv` round trip.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout/stderr so logs aren't lost on crash.
ENV PYTHONUNBUFFERED=1
# /shared and /contracts mirror the docker-compose bind-mount layout so the
# same PYTHONPATH works whether the source comes from this image or a volume.
ENV PYTHONPATH=/app:/contracts:/shared
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# System dependencies for OCR and OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (from the lockfile only) so this layer is cached
# independently of application code changes. Only base dependencies are
# installed: PyMuPDF for digital PDFs, OpenRouter for scanned files, and the
# Tesseract fallback. The "complete" (Paddle/EasyOCR) and "trocr" extras stay
# opt-in for local profiles — add `--extra complete --extra trocr` if needed.
COPY backend-ocr/pyproject.toml backend-ocr/uv.lock ./
RUN uv sync --frozen --no-install-project

# Packages shared across services; copied (not flattened into /app) so they
# resolve via PYTHONPATH exactly like the compose bind mounts do.
COPY shared/ /shared
COPY contracts/ /contracts

# Copy the source code into the container
COPY backend-ocr/ .
RUN uv sync --frozen

# Expose the port that the application listens on
EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]
