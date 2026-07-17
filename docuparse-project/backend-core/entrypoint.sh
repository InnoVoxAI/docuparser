#!/bin/sh
set -e

echo "[entrypoint] Applying public schema migrations..."
python manage.py migrate_schemas --shared

# Tenant schemas must be provisioned BEFORE seeding: seed_data writes per-tenant
# rows (SchemaConfig/LayoutConfig) inside schema_context(<tenant>). If a tenant
# schema exists but is empty (e.g. created by tenants.0003 but never migrated),
# those writes fall through search_path to stale public.documents_* tables and
# fail. Migrating tenants first gives each schema its own tables, so the seed
# writes land where they should.
echo "[entrypoint] Applying tenant schema migrations..."
python manage.py migrate_schemas

echo "[entrypoint] Seeding default tenant, admin user, and permissions..."
python manage.py seed_data

echo "[entrypoint] Starting server..."
exec python manage.py runserver 0.0.0.0:8000
