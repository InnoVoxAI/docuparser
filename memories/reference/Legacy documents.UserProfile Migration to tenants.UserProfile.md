---
title: Legacy documents.UserProfile Migration to tenants.UserProfile
type: reference
permalink: docuparser/reference/legacy-documents.user-profile-migration-to-tenants.user-profile
tags:
- rbac
- migration
- legacy
- users
---

## Context

Task 13 (roles_permission_adjustments branch) audited whether the legacy
`documents.UserProfile` model (CharField `role`, choices operator/supervisor/admin)
is still referenced anywhere, now that RBAC uses `tenants.UserProfile` with a
`role_ref` FK to `users.Role` (which has `is_platform_role`).

## Finding: already fully migrated, no action needed

- `documents/models.py` has no `UserProfile` class — confirmed via grep.
- No code imports `UserProfile` from `documents.models`; no references to the
  `documents_userprofile` table outside migration files.
- No references to the legacy `supervisor` role string outside migrations
  (current RBAC roles are `operator` / `tenantAdmin` / `admin`, see
  `users/management/commands/seed_data.py`).
- `related_name="docuparse_profile"` is defined once in *live* code, on
  `tenants.UserProfile` (`tenants/models.py:50`). The only other place that
  string appears is the historical `documents/migrations/0001_initial.py`
  (dead migration, table since dropped) — not live code.
- Every consumer (`users/permissions.py:20`, `users/serializers.py:62,72,93`,
  `users/user_views.py`) accesses `request.user.docuparse_profile` /
  `obj.docuparse_profile` generically, which now resolves only to
  `tenants.UserProfile`.

## Migration chain (verified applied in dev DB)

- `tenants/0003_migrate_legacy_tenant_data` copies legacy Tenant/UserProfile
  rows into the `tenants` app models.
- `documents/0011_remove_tenant_fk` (depends on `tenants/0003`) then runs
  `migrations.DeleteModel("UserProfile")` and `DeleteModel("Tenant")`,
  dropping the legacy tables from the `documents` app.
- `showmigrations documents tenants` in the dev container shows both fully
  applied ([X]), in the correct order.
- DB introspection confirms: `documents_userprofile` table does not exist;
  `tenants_userprofile` exists with columns
  `[created_at, updated_at, id, user_id, tenant_id, role_ref_id]` — no
  legacy `role` CharField, just the `role_ref_id` FK.
- Runtime check via Django shell: an existing user's
  `docuparse_profile` is a `tenants.models.UserProfile` instance with a
  working `role_ref` (`is_platform_role` populated correctly).

## Outcome

No refactor needed — the model was already fully removed and migrated
before this task started. No rollback risk. Did not add a `.aiignore` entry
for the legacy migration files (none exists in the repo yet, and the
migration history file is small/inert — revisit only if `.aiignore` gets
introduced for other reasons).

See also: [[Privilege Escalation Guard (task 5)]], [[RBAC Permission Matrix]] (if/when written).
