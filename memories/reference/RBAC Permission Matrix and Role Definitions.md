---
title: RBAC Permission Matrix and Role Definitions
type: reference
permalink: docuparser/reference/rbac-permission-matrix-and-role-definitions
tags:
- rbac
- roles
- permissions
- security
---

## Overview

RBAC rework done on branch `roles_permission_adjustments` (2026-07-28). Three
roles are seeded by `users/management/commands/seed_data.py` (`ROLE_SPECS`):

| Role | `is_platform_role` | Permissions |
|---|---|---|
| `admin` | **True** | all 9: inbox.view, documents.send, documents.validate, models.create, models.edit, operations.access, users.manage, roles.manage, tenants.manage |
| `tenantAdmin` | False | inbox.view, documents.send, documents.validate, models.create, models.edit, operations.access, users.manage |
| `operator` | False | inbox.view, documents.send, documents.validate, operations.access |

Full permission catalog (`PERMISSIONS` in the same file): `inbox.view`,
`documents.send`, `documents.validate`, `models.create`, `models.edit`,
`operations.access`, `users.manage`, `roles.manage`, `tenants.manage`.

## `is_platform_role` field

Added to `users.Role` (model: `docuparse-project/backend-core/users/models.py`).
Marks roles that only a platform-level admin should be able to grant — currently
only `admin`. Distinguishes "can manage users within a tenant" (`users.manage`,
held by tenantAdmin) from "can grant platform-level access" (`is_platform_role`).

Exposed over the API (added in task 10, previously missing):
- `RoleListSerializer` (`GET /api/ocr/roles`)
- nested `role` dict in `UserMeSerializer` (`GET /api/auth/me`) and
  `UserListSerializer` (`GET /api/ocr/users`)

All three live in `docuparse-project/backend-core/users/serializers.py`.

## Privilege escalation protection

`user_detail_update_view` in
`docuparse-project/backend-core/users/user_views.py` (~L100): when a
`role_id` update targets a role with `is_platform_role=True`, the acting
user's own `docuparse_profile.role_ref.is_platform_role` must also be
`True`, or the request gets 403 ("Você não tem permissão para atribuir
roles de plataforma."). This is what stops a tenantAdmin (who holds
`users.manage`) from promoting anyone — including themselves — to `admin`.

Frontend UX layer (not a security boundary — the backend check above is):
`UserFormModal.tsx` filters roles with `is_platform_role=true` out of the
role-selector dropdown unless the acting user is themselves a platform
admin. Acting user's platform-admin status is read by matching their own
email against the already-fetched `/api/ocr/users` list (avoids needing a
separate `/me` field). See `GerenciarUsuarios.tsx` and `UserFormModal.tsx`
under `docuparse-project/frontend/src/modules/admin/components/`.

## Permissions that were previously unenforced

Before this work, `models.edit` and `operations.access` existed as permission
codes but weren't actually checked on the endpoints they should gate:

- **`models.edit`** now required (via `require_permission`) on 6 endpoints in
  `docuparse-project/backend-core/documents/views.py`: `schema_configs_view`,
  `schema_config_detail_view`, `layout_configs_view`,
  `integration_settings_view`, `ocr_settings_view`, `email_settings_view`.
- **`operations.access`** now required on 3 DLQ endpoints in the same file:
  `dlq_summary_view`, `dlq_events_view`, `dlq_requeue_view`.
- Frontend nav/route guards for the Configurações screen were updated to
  match: `frontend/src/app/navigation.ts` and
  `frontend/src/modules/settings/routes/SettingsRoute.tsx` now gate on
  `models.edit` instead of the unrelated `roles.manage`.

Service-to-service calls (`request.auth == "service_token"`, via
`DocuparseAuthentication`'s internal-token fallback) bypass all of the above
unconditionally — used by langextract/other backend services.

## Testing approach

Consolidated suite: `docuparse-project/backend-core/users/tests/test_rbac_enforcement.py`.
Builds its fixtures directly from `seed_data.PERMISSIONS`/`ROLE_SPECS` (not
hand-rolled roles) so tests can't drift from the real production permission
matrix. Covers:
- `models.edit` matrix: operator 403, tenantAdmin 200, admin 200 (all 6 endpoints)
- `operations.access` matrix: operator/tenantAdmin/admin all 200 (3 DLQ endpoints, incl. dry-run requeue)
- Escalation guard: tenantAdmin→admin 403, tenantAdmin→tenantAdmin 200, admin→admin 200
- Service-token bypass still works on both permission types

Plus narrower per-feature tests alongside the existing suites:
`test_user_management.py::PrivilegeEscalationTest`, `test_role_management.py`,
`test_auth_views.py`, and pre-existing `documents/tests/test_api.py` coverage
(schema-configs permission gate, service-token gate regression tests).

Frontend: `frontend/src/__tests__/permissions.test.tsx` and `flows.test.tsx`
cover nav visibility and the platform-role filtering in the user form modal.

## Migration steps taken (task order)

1. `is_platform_role` field on `Role` model + migration (task 1) — see [[Role.is_platform_role field added]]
2. `seed_data.py` rewritten for the 3-role permission matrix above (task 2) — see [[seed_data.py: three roles with permission matrix]]
3–4. `models.edit` / `operations.access` enforcement added to the document
   endpoints (tasks 3–4) — see [[models.edit permission enforced on schema/layout/settings endpoints]]
5. Privilege escalation guard in `user_detail_update_view` (task 5)
6–7. Frontend nav + settings route guard switched to `models.edit` (tasks 6–7)
8. `is_platform_role` added to frontend `AdminRole`/`AdminRoleRef` TS types (task 8)
9. `UserFormModal` filters platform roles from the selector for non-platform admins (task 9)
10. Backend serializers updated to actually send `is_platform_role` (task 10) —
    this had to land after task 9 since the frontend filter was written to be a
    safe no-op until the field existed on the wire
11. Consolidated RBAC test suite (task 11)
13. Audited legacy `documents.UserProfile` — already fully removed/migrated,
    no action needed, see [[Legacy documents.UserProfile Migration to tenants.UserProfile]]

## Related

[[Legacy documents.UserProfile Migration to tenants.UserProfile]]
[[Role.is_platform_role field added]]
[[seed_data.py: three roles with permission matrix]]
[[models.edit permission enforced on schema/layout/settings endpoints]]
