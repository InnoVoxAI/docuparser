# Tasks: Multi-Tenancy — PostgreSQL Schema-per-Tenant

**Input**: Design documents from `docs/specs/010-multi-tenancy-schemas/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no conflicting dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- All paths relative to `docuparse-project/backend-core/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install django-tenants, create the `tenants` app scaffold, and wire configuration.
No user story work can begin until this phase is done.

- [ ] T001 Add `django-tenants` to `docuparse-project/backend-core/requirements.txt` (latest stable, Django 5.x compatible)
- [ ] T002 Create `docuparse-project/backend-core/tenants/` app with `apps.py`, `__init__.py`, `migrations/__init__.py`, empty `models.py`, `middleware.py`, `views.py`, `serializers.py`, `urls.py`
- [ ] T003 [P] Update `core/settings.py`: replace `INSTALLED_APPS` with `SHARED_APPS` / `TENANT_APPS` split per data-model.md; add `TENANT_MODEL = "tenants.Tenant"`, `TENANT_DOMAIN_MODEL = "tenants.Domain"`, `DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]`
- [ ] T004 [P] Configure `core/urls.py` for django-tenants URL routing: split into public URL conf and tenant URL conf per django-tenants documentation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Refactor all models to the public/tenant schema split. No user story can be
tested until schema routing is established and the existing `tenant` FK is removed.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Move `Tenant` model to `tenants/models.py` — inherit from `django_tenants.models.TenantMixin` + existing `TimeStampedModel`; add `schema_name = CharField(max_length=63, unique=True)` (value: `"tenant_" + slug`); set `auto_create_schema = True`
- [ ] T006 [P] Add `Domain` model to `tenants/models.py` inheriting `django_tenants.models.DomainMixin`; add `tenant = FK(Tenant)`
- [ ] T007 Move `UserProfile` model from `documents/models.py` into `tenants/models.py` so it lives in the public schema (it must resolve `user → tenant` before schema routing)
- [ ] T008 Create initial migration `tenants/migrations/0001_initial.py` for Tenant, Domain, UserProfile models
- [ ] T009 Write data migration `tenants/migrations/0002_populate_schema_name_and_domain.py` (RunPython): populate `schema_name = "tenant_" + slug` for every existing Tenant row; create one placeholder `Domain` row per tenant
- [ ] T010 Remove `tenant = FK(Tenant)` from per-tenant document models in `documents/models.py`: `Document`, `DocumentEvent`, `ExtractionResult`, `ExtractionFieldVersion`, `ValidationDecision`, `ERPIntegrationAttempt`; update composite indexes (remove `tenant` field from multi-column indexes per data-model.md)
- [ ] T011 [P] Remove `tenant = FK(Tenant)` / `tenant = OneToOneField(Tenant)` from settings models in `documents/models.py`: `IntegrationSettings`, `OCRSettings`, `EmailSettings`, `SchemaConfig`, `LayoutConfig`; update `UniqueConstraint` definitions to drop `tenant` field
- [ ] T012 Remove `UserProfile` import and model definition from `documents/models.py` (it now lives in `tenants/models.py`); update all `documents/` imports that reference `UserProfile`
- [ ] T013 Create Django migration in `documents/migrations/` to drop the `tenant` FK column and associated indexes from all per-tenant models (separate from `tenants/` migrations)
- [ ] T014 [P] Update `users/user_views.py` and `users/serializers.py` to import `UserProfile` from `tenants.models` instead of `documents.models`
- [ ] T015 [P] Update `documents/views.py` imports: replace `UserProfile` import from `documents.models` with `tenants.models`; remove explicit `tenant`-based queryset filters (schema routing makes them implicit)

**Checkpoint**: All models refactored, migrations created, settings configured. Schema routing middleware work can now begin.

---

## Phase 3: User Story 3 — JWT-Based Tenant Resolution (P1)

**Goal**: Every authenticated request automatically routes to the correct tenant schema using
the JWT `tenant` claim. Service-token calls use `X-Tenant` header.

**Independent Test**: Authenticate as a user with `UserProfile.tenant.slug = "acme"`, decode
the returned JWT access token, confirm `"tenant": "acme"` claim is present; make a protected
API call and confirm it hits the `tenant_acme` schema (no 500 errors, no public-schema data).

- [ ] T016 [US3] Implement `JWTTenantMiddleware` in `tenants/middleware.py`: subclass `BaseTenantMiddleware`, override `get_tenant(model, hostname, request)` to extract `tenant` claim from JWT payload (without full validation — just claims decode); look up `Tenant.objects.using("default").get(slug=claim, is_active=True)` against the public schema; raise `SuspiciousOperation` for missing/invalid/inactive tenant
- [ ] T017 [US3] Add `X-Tenant` header fallback in `JWTTenantMiddleware.get_tenant()`: when `request.META.get("HTTP_AUTHORIZATION", "").startswith("Bearer ")` matches the static service token, resolve tenant from `request.META.get("HTTP_X_TENANT")` instead of JWT claim; return 401 if header is absent or unknown
- [ ] T018 [US3] Add inactive tenant guard in `JWTTenantMiddleware`: when `Tenant.is_active = False`, raise `PermissionDenied` so Django returns 403 before any ORM query runs in the tenant schema
- [ ] T019 [US3] Register `JWTTenantMiddleware` as the FIRST entry in `MIDDLEWARE` in `core/settings.py` (before `SecurityMiddleware`)
- [ ] T020 [US3] Override `TokenObtainPairSerializer` in `users/auth_views.py` (or a new `tenants/serializers.py` JWT serializer): add `token["tenant"] = user.docuparse_profile.tenant.slug` in `get_token()` classmethod; update `TokenObtainPairView` to use this serializer
- [ ] T021 [P] [US3] Write unit test `tests/unit/test_jwt_tenant_claim.py`: assert `tenant` claim appears in access token after successful login; assert missing `UserProfile` raises a clear error

**Checkpoint**: `POST /api/auth/login/` returns JWT with `tenant` claim; subsequent requests hit the correct schema.

---

## Phase 4: User Story 2 — Tenant Provisioning (P1)

**Goal**: Admin can create a new tenant via API; the system automatically creates the
PostgreSQL schema, runs migrations, and seeds default roles/permissions.

**Independent Test**: POST to `/api/admin/tenants/` with `{slug: "beta", name: "Beta Corp"}`;
inspect PostgreSQL; confirm `tenant_beta` schema exists with all tenant-app tables; confirm
default Role/Permission rows are seeded.

- [ ] T022 [US2] Add `tenants.manage` permission code to the `Permission` seed data (management command or data migration in `users/` or `tenants/`)
- [ ] T023 [US2] Implement `TenantProvisionView` in `tenants/views.py` (POST `/api/admin/tenants/`): validate `slug` (regex `[a-z0-9-]`, max 50), check uniqueness, call `tenant.save()` (triggers `auto_create_schema`), seed default Role/Permission rows into the new schema, return 201 with tenant data; return 409 on duplicate slug; return 500 with rollback on schema creation failure
- [ ] T024 [P] [US2] Implement `TenantListView` in `tenants/views.py` (GET `/api/admin/tenants/`): return list of all tenants with `{id, slug, name, schema_name, is_active, created_at}`; wrap in standard API envelope `{data, error, meta: {count}}`
- [ ] T025 [P] [US2] Implement `TenantUpdateView` in `tenants/views.py` (PATCH `/api/admin/tenants/{slug}/`): allow updating `name` and `is_active`; guard against deactivating the last active tenant (return 403); return 404 if slug not found
- [ ] T026 [US2] Create `TenantSerializer`, `TenantCreateSerializer`, `TenantUpdateSerializer` in `tenants/serializers.py` per contracts/tenant-admin-api.md
- [ ] T027 [US2] Wire tenant admin URLs in `tenants/urls.py` and include in the public URL conf in `core/urls.py`
- [ ] T028 [US2] Write management command `documents/management/commands/migrate_to_schemas.py`: iterate all Tenant rows; call `create_schema(check_if_exists=True)` + `migrate_schemas --schema=<schema_name>`; copy rows from public shared tables into per-tenant schema using raw SQL; accept `--dry-run` and `--tenant-slug` flags; print row counts before/after; wrap per-tenant work in `transaction.atomic()`
- [ ] T029 [P] [US2] Write integration test `tests/integration/test_tenant_provisioning.py` (uses `TenantTestCase`): POST creates schema; duplicate slug returns 409; schema contains expected tables after creation

**Checkpoint**: New tenants can be created via API; schemas are provisioned automatically.

---

## Phase 5: User Story 1 — Tenant Data Isolation (P1)

**Goal**: An authenticated user from Tenant A sees only their data across all endpoints.
No cross-tenant data leakage is possible.

**Independent Test**: Create two tenants (A and B) each with 3 documents; authenticate as
Tenant A user; call `GET /api/documents/`; assert exactly 3 documents returned; request a
Tenant B document UUID; assert 404.

- [ ] T030 [US1] Update `documents/views.py` list views (documents, events, schema configs, layout configs, settings): remove all explicit `filter(tenant=...)` clauses — data isolation is now enforced by the schema; confirm querysets no longer reference `tenant` field
- [ ] T031 [US1] Update `documents/serializers.py`: remove `tenant` / `tenant_id` fields from all serializer classes that previously exposed them; ensure no cross-schema FK references remain
- [ ] T032 [US1] Update `users/user_views.py`: scope user list queries to the current tenant using `request.tenant` (available via django-tenants middleware on `request`); users not belonging to `request.tenant` must not be returned
- [ ] T033 [US1] Write integration test `tests/integration/test_tenant_isolation.py` (uses `TenantTestCase`, requires PostgreSQL): assert `GET /api/documents/` with Tenant A JWT returns 0 documents from Tenant B; assert `GET /api/documents/{tenant_b_doc_id}/` returns 404; assert `GET /api/documents/` with invalid tenant JWT returns 401
- [ ] T034 [P] [US1] Write integration test for inactive tenant guard: deactivate a tenant; assert all subsequent JWT-authenticated requests return 403

**Checkpoint**: Full cross-tenant isolation verified. US1 acceptance scenarios pass.

---

## Phase 6: User Story 4 — Tenant-Scoped Settings (P2)

**Goal**: Each tenant's OCR, integration, email, schema, and layout settings are
fully isolated. One tenant's changes cannot affect another's.

**Independent Test**: Set `OCRSettings.digital_pdf_engine = "docling"` in Tenant A's schema;
read OCR settings as Tenant B; confirm Tenant B value is unchanged.

- [ ] T035 [US4] Update `documents/views.py` settings endpoints (`ocr_settings`, `integration_settings`, `email_settings`, `schema_configs`, `layout_configs`): remove `filter(tenant=...)` / `get(tenant=...)` calls; use `get_or_create()` or `filter()` without tenant argument (implicit schema scope)
- [ ] T036 [P] [US4] Update `IntegrationSettings`, `OCRSettings`, `EmailSettings` in `documents/models.py`: since `tenant` OneToOneField is removed (done in Phase 2), enforce singleton-per-schema via an application-level check or `UniqueConstraint(fields=[], condition=Q())` Django trick; document the enforcement strategy in code
- [ ] T037 [US4] Write integration test `tests/integration/test_tenant_settings.py`: update OCR settings for Tenant A; read OCR settings as Tenant B JWT; assert values differ; update layout config for Tenant A; assert Tenant B layout config unchanged

**Checkpoint**: All four user stories independently verified and functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Data migration, CI configuration, and operational hardening.

- [ ] T038 Add `pytest` marker `tenant_db` and configure `conftest.py` to skip schema-routing tests when `POSTGRES_HOST` env var is absent (these tests cannot run on SQLite)
- [ ] T039 [P] Update `docker-compose.yml` / CI config to ensure `POSTGRES_HOST` is set in the test environment for tenant integration tests
- [ ] T040 [P] Update `commands.md` in the repo root with tenant provisioning commands: `migrate_schemas --shared`, `migrate_schemas`, `migrate_to_schemas --dry-run`, and `POST /api/admin/tenants/` example
- [ ] T041 Run `migrate_to_schemas` against the existing development database and verify row counts; document any issues found
- [ ] T042 [P] Remove any leftover `tenant_id` column references in `documents/services/` (event consumers, ERP publisher, OCR processor, DLQ inspector) that previously used explicit tenant filtering
- [ ] T043 Audit all `documents/tests/` for references to `Tenant` model imported from `documents.models`; update to import from `tenants.models`
- [ ] T044 [P] Constitution compliance check: confirm all new files are ≤ 400 lines, all functions ≤ 50 lines, type hints present throughout `tenants/` app

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup                    ← Start immediately
    │
    ▼
Phase 2: Foundational             ← Blocks ALL user stories
    │
    ├─────────────────────┐
    ▼                     ▼
Phase 3: US3 (JWT)     Phase 4: US2 (Provisioning)
    │                     │
    └──────────┬──────────┘
               ▼
         Phase 5: US1 (Isolation)
               │
               ▼
         Phase 6: US4 (Settings)
               │
               ▼
         Phase 7: Polish
```

### User Story Dependencies

- **US3 (JWT, Phase 3)**: Depends only on Phase 2 — implement middleware + login token embedding
- **US2 (Provisioning, Phase 4)**: Depends only on Phase 2 — implement provisioning endpoint (can proceed alongside US3)
- **US1 (Isolation, Phase 5)**: Depends on US3 (need working auth) and US2 (need multiple tenants to test isolation)
- **US4 (Settings, Phase 6)**: Depends on Phase 2 model changes only; can proceed after Foundational

### Within Each Phase

- Tasks marked `[P]` can run in parallel within their phase
- T005 → T006 → T007 → T008 (strict order in Phase 2: model → model → migration → data migration)
- T010 and T011 can run in parallel (different model groups within `documents/models.py` — but edit the same file, so coordinate)
- T023 → T026 (Provisioning view after serializers in Phase 4)
- T030 → T033 (views update before isolation tests)

---

## Parallel Execution Examples

### Phase 2 — Parallel tasks after T005/T006/T007

```text
T010 — Remove tenant FK from document models in documents/models.py
T011 — Remove tenant FK from settings models in documents/models.py  (different model classes, same file — coordinate)
T014 — Update users/user_views.py imports
T015 — Update documents/views.py imports
```

### Phase 4 — Parallel provisioning tasks

```text
T024 — TenantListView in tenants/views.py
T025 — TenantUpdateView in tenants/views.py
T029 — Integration test for provisioning
```

### Phase 7 — Parallel polish tasks

```text
T039 — CI/Docker config update
T040 — Update commands.md
T042 — Clean up documents/services/ tenant references
T044 — Constitution compliance check
```

---

## Implementation Strategy

### MVP First (US3 + US2 — enables first real tenant login)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational model refactor
3. Complete Phase 3: US3 (JWT resolution) — first milestone: login returns tenant claim
4. Complete Phase 4: US2 (Provisioning) — second milestone: can create a second tenant
5. **STOP and VALIDATE**: two tenants exist, both can login with isolated JWTs
6. Proceed to Phase 5 (US1 isolation verification)

### Incremental Delivery

| Milestone | After completing | What works |
|-----------|------------------|------------|
| Foundation | Phase 1 + 2 | App boots with django-tenants; models refactored |
| Auth | Phase 3 | JWT carries tenant claim; schema switching on every request |
| Onboarding | Phase 4 | New tenants can be created via API |
| Isolation | Phase 5 | Cross-tenant leak tests pass; MVP shippable |
| Full SaaS | Phase 6 | Per-tenant settings fully isolated |
| Production | Phase 7 | Data migrated; CI green |

---

## Notes

- `[P]` tasks touch different files and have no incomplete dependencies — safe to parallelize
- `[Story]` label maps each task to a user story for traceability (US1–US4 from spec.md)
- Phase 2 (T010, T011) edits the same `documents/models.py` file — serialize or split into separate commits
- Schema-routing integration tests MUST run against PostgreSQL (`POSTGRES_HOST` required)
- `TenantTestCase` wraps each test in a fresh schema — use it for all Phase 5/6 integration tests
- The `migrate_to_schemas` command (T028) should be run with `--dry-run` first in any environment
