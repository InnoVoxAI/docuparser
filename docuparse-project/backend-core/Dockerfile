FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend-core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend-core/ .
COPY shared/docuparse_events ./docuparse_events
COPY shared/docuparse_observability ./docuparse_observability
COPY shared/docuparse_storage ./docuparse_storage
COPY contracts/events ./events

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_data && python manage.py runserver 0.0.0.0:8000"]
