FROM python:3.13-slim

WORKDIR /app

COPY backend-com/pyproject.toml .
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings python-multipart pyjwt structlog toml redis

COPY backend-com/src ./src
COPY shared/ /shared
COPY contracts/ /contracts

ENV PYTHONPATH=/app/src:/contracts:/shared

CMD ["uvicorn", "backend_com.api.app:app", "--host", "0.0.0.0", "--port", "8070"]
