#!/bin/sh
set -e

echo "[entrypoint] Applying public schema migrations..."
python manage.py migrate_schemas --shared

echo "[entrypoint] Seeding default tenant, admin user, and permissions..."
python manage.py seed_data

echo "[entrypoint] Applying tenant schema migrations..."
python manage.py migrate_schemas

echo "[entrypoint] Starting server..."
exec python manage.py runserver 0.0.0.0:8000
