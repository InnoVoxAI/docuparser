FROM python:3.13-slim

WORKDIR /app

COPY langextract-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY langextract-service/ .
COPY shared/docuparse_events ./docuparse_events
COPY shared/docuparse_observability ./docuparse_observability
COPY shared/docuparse_storage ./docuparse_storage
COPY contracts/events ./events

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8091"]
