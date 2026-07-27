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

WORKDIR /app

# Install dependencies first (from the lockfile only) so this layer is cached
# independently of application code changes.
COPY langextract-service/pyproject.toml langextract-service/uv.lock ./
RUN uv sync --frozen --no-install-project

# Packages shared across services; copied (not flattened into /app) so they
# resolve via PYTHONPATH exactly like the compose bind mounts do.
COPY shared/ /shared
COPY contracts/ /contracts

# Copy the source code into the container
COPY langextract-service/ .
RUN uv sync --frozen

# Expose the port that the application listens on
EXPOSE 8091

CMD ["uv", "run", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8091"]
