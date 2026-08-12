FROM python:3.12-slim

WORKDIR /app

COPY camunda-workers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Packages shared across services; copied (not flattened into /app/src) so
# they resolve via PYTHONPATH exactly like the docker-compose bind mounts do.
COPY shared/ /shared
COPY contracts/ /contracts

COPY camunda-workers/src/ ./src/

# /shared and /contracts mirror the docker-compose bind-mount layout (see
# other services' Dockerfiles) so configure_tracing() and friends resolve
# whether the source comes from this image or a dev volume mount.
ENV PYTHONPATH=/app/src:/contracts:/shared

CMD ["python", "src/main.py"]
