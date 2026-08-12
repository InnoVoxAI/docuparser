---
title: models.edit permission enforced on schema/layout/settings endpoints
type: note
permalink: docuparser/features/models.edit-permission-enforced-on-schema-layout-settings-endpoints
tags:
- multi-tenancy
- backend-core
- documents
- permissions
---

## Status
Done (2026-07-28), verified end-to-end with pytest against a real Postgres.

## What changed
- `docuparse-project/backend-core/documents/views.py`: added `@authentication_classes([DocuparseAuthentication])` + `@permission_classes([require_permission("models.edit")])` to six endpoints — `schema_configs_view`, `schema_config_detail_view`, `layout_configs_view`, `integration_settings_view`, `ocr_settings_view`, `email_settings_view` — matching the pattern already used by `inbox.view`/`documents.validate` endpoints in the same file. Dropped the now-redundant `_internal_token_error(request)` manual check from these six (still used elsewhere in the file, so not deleted — `HasDocuparsePermission` already allows `request.auth == "service_token"`).
- `docuparse-project/backend-core/documents/tests/test_api.py`: two test fixtures needed `models.edit` granted to their test users, since these endpoints no longer accept any authenticated user unconditionally:
  - `DocumentsAPITests.setUp`'s shared "Operador" role gained `models.edit` (it drives schema/layout/settings endpoint tests, not just inbox/validate).
  - `InternalServiceTokenGateTests.setUp`'s bare user now gets a `Role`+`UserProfile` with `models.edit` (this class is a regression guard for the old `_internal_token_error` gate on `schema-configs`; that endpoint's access model changed, so the "authenticated JWT user is accepted" case now needs the permission — `service_token` bypass and the "no credentials → 401" case were unaffected).

## Verification method (important for next time)
This devcontainer *does* have a reachable Postgres — hostname `postgres`, exposed via `.devcontainer/docker-compose.yml` (docker-in-docker feature, network `docuparser_net`). Run Django/pytest commands through `/docuparser/run_script.sh <cmd>`, which loads `/docuparser/.env` and sets `PYTHONPATH` before exec'ing. Earlier assumption in [[Role.is_platform_role field added]] and [[seed_data.py: three roles with permission matrix]] that "no Postgres is reachable in this devcontainer" was wrong — it just needs `run_script.sh`, not raw `docker` commands.
- `documents/tests/test_api.py` has 8 pre-existing failures unrelated to any of these 3 tasks (S3/MinIO/event-bus/OCR timing flakiness) — confirmed by diffing a baseline run (views.py reverted to HEAD) against the post-change run. Use that baseline-diff technique to separate real regressions from pre-existing flakiness in this suite.
- Some tests in `DocumentsAPITests` are order-dependent/flaky in the full-file run but pass in isolation (e.g. `test_inbox_and_detail_endpoints`) — not a real regression signal.

## Context
Completes the multi-tenancy role/permission chain: [[Role.is_platform_role field added]] (task #1) → [[seed_data.py: three roles with permission matrix]] (task #2) → this (task #3). Related to [[010-multi-tenancy-schemas plan]].
