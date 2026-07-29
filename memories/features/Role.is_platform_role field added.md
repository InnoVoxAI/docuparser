---
title: Role.is_platform_role field added
type: note
permalink: docuparser/features/role.is-platform-role-field-added
tags:
- multi-tenancy
- backend-core
- users
---

## Status
Done (confirmed by user 2026-07-28, verified locally via `migrate_schemas --shared`).

## What changed
- Added `is_platform_role = models.BooleanField(default=False)` to `Role` in `docuparse-project/backend-core/users/models.py`.
- New migration `docuparse-project/backend-core/users/migrations/0002_role_is_platform_role.py` (AddField, depends on `0001_initial`).

## Context
- `users` app is in `SHARED_APPS` (public schema) in `docuparse-project/backend-core/core/settings.py`, not `TENANT_APPS` — so this field lives on the shared/public schema, applied via `migrate_schemas --shared`, not per-tenant.
- Part of work related to [[010-multi-tenancy-schemas plan]] — `is_platform_role` distinguishes platform-level roles from tenant-scoped roles.
- Tracked as Task Master task #1 in `.taskmaster/tasks/tasks.json`.

## Environment note
**Correction (2026-07-28, see [[models.edit permission enforced on schema-layout-settings endpoints]]):** Postgres *is* reachable in this devcontainer, at hostname `postgres` (docker-in-docker, `.devcontainer/docker-compose.yml`). Run Django commands via `/docuparser/run_script.sh <cmd>`, which loads `/docuparser/.env` and sets `PYTHONPATH`. Don't assume no-DB again — try `run_script.sh` first.
