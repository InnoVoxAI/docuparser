---
title: 'seed_data.py: three roles with permission matrix'
type: note
permalink: docuparser/features/seed-data.py-three-roles-with-permission-matrix
tags:
- multi-tenancy
- backend-core
- users
- seed-data
---

## Status
Done (confirmed by user 2026-07-28, verified locally via `manage.py seed_data`).

## What changed
- `docuparse-project/backend-core/users/management/commands/seed_data.py`: replaced single `admin` `Role.objects.get_or_create` with a `ROLE_SPECS` list (`RoleSpec` TypedDict) defining three roles — `admin` (is_platform_role=True, 9 perms), `tenantAdmin` (False, 7 perms), `operator` (False, 4 perms).
- Loop creates/updates each role via `get_or_create`, sets its permission set from `Permission.objects.filter(code__in=...)`, and sets `is_platform_role`. Idempotent — re-running doesn't duplicate or drop roles.
- `roles_by_name["admin"]` replaces the old single `role` variable so downstream `UserProfile.role_ref=role` (used when seeding admin users per tenant) is unchanged — every seeded admin user still gets the `admin` role, not `tenantAdmin`/`operator`.

## Context
- Builds directly on [[Role.is_platform_role field added]] (task #1) — this is Task Master task #2, depended on task #1's migration.
- Permission matrix source: task #2 implementation details in `.taskmaster/tasks/tasks.json`.

## Environment note
**Correction (2026-07-28, see [[models.edit permission enforced on schema-layout-settings endpoints]]):** Postgres *is* reachable in this devcontainer, at hostname `postgres` (docker-in-docker, `.devcontainer/docker-compose.yml`). Run Django commands via `/docuparser/run_script.sh <cmd>`, which loads `/docuparser/.env` and sets `PYTHONPATH`. Don't assume no-DB again — try `run_script.sh` first.
