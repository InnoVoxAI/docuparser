# Implementation Plan: Multi-Tenancy — PostgreSQL Schema-per-Tenant

**Branch**: `010-multi-tenancy-schemas` | **Date**: 2026-06-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/010-multi-tenancy-schemas/spec.md`

## Summary

Convert DocuParser's Django backend from a shared-schema multi-tenancy model (all tenants in
one PostgreSQL schema filtered by `tenant` FK) to a schema-per-tenant model using
`django-tenants`. Each tenant's operational data (`Document`, `ExtractionResult`, etc.) lives
in an isolated PostgreSQL schema named `tenant_<slug>`. Shared tables (`Tenant`/`Client`,
`UserProfile`, `auth.User`, `Role`, `Permission`) remain in the `public` schema. Tenant
resolution uses the JWT access token's `tenant` claim rather than subdomain routing.

## Technical Context

**Language/Version**: Python 3.11+, Django 5.0.1

**Primary Dependencies**: django-tenants (latest stable, 3.x), djangorestframework 3.14,
djangorestframework-simplejwt 5.3, psycopg2-binary

**Storage**: PostgreSQL — one database, N+1 schemas (`public` + one per tenant)

**Testing**: pytest-django; integration tests MUST use real PostgreSQL (no SQLite for
multi-tenant tests — schema commands are PostgreSQL-only)

**Target Platform**: Linux server (Docker/Docker Compose)

**Project Type**: Web service (Django REST API)

**Performance Goals**: API p95 ≤ 200 ms for non-processing endpoints (constitution §IV);
schema switching overhead must be negligible (single `SET search_path` per connection)

**Constraints**: Django's SQLite fallback (used in dev) is incompatible with schema-per-tenant;
tests that exercise schema routing MUST run against PostgreSQL

**Scale/Scope**: Tens of tenants initially; schema-per-tenant scales to hundreds before
connection pool pressure becomes relevant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| **I. Code Quality** | ✅ Tenant middleware and model changes MUST use type hints; no file may exceed 400 lines |
| **I. Security** | ✅ CRITICAL — cross-tenant data leakage is an OWASP-class vulnerability; schema isolation + JWT claim validation are the primary controls |
| **II. Testing** | ✅ Integration tests REQUIRED for schema routing, tenant provisioning, and JWT tenant claim; SQLite fallback explicitly excluded for these tests |
| **II. Coverage** | ⚠️ New middleware and provisioning logic MUST reach ≥ 80% coverage; schema-routing path MUST reach ≥ 90% |
| **III. API Envelope** | ✅ All new endpoints follow `{ data, error, meta }` envelope |
| **IV. Performance** | ✅ Schema switching is a single SQL `SET` command; p95 budget unchanged |
| **IV. Startup** | ✅ django-tenants middleware adds no meaningful startup cost |

**Violations**: None. No complexity-tracking entry required.

## Project Structure

### Documentation (this feature)

```text
docs/specs/010-multi-tenancy-schemas/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── tenant-admin-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
docuparse-project/backend-core/
├── core/
│   ├── settings.py           # django-tenants config (TENANT_MODEL, SHARED_APPS, TENANT_APPS)
│   └── urls.py               # split public/tenant URL routing
├── tenants/                  # NEW app — public-schema models & provisioning
│   ├── apps.py
│   ├── models.py             # Client (Tenant + TenantMixin), Domain, updated UserProfile
│   ├── middleware.py         # JWTTenantMiddleware (resolves schema from JWT claim)
│   ├── views.py              # TenantProvisionView (POST /api/admin/tenants/)
│   ├── serializers.py
│   ├── migrations/
│   └── tests/
│       ├── test_middleware.py
│       └── test_provisioning.py
├── documents/
│   ├── models.py             # REMOVE tenant FK; keep all other fields
│   ├── migrations/           # Migration to drop tenant FK + drop Tenant/UserProfile models
│   └── management/commands/
│       └── migrate_to_schemas.py  # One-shot data migration
└── users/
    ├── models.py             # Role, Permission stay here (public schema)
    └── auth_views.py         # Augmented: embeds tenant claim in JWT

tests/
├── integration/
│   └── test_tenant_isolation.py   # Cross-tenant leak tests (PostgreSQL only)
└── unit/
    └── test_jwt_tenant_claim.py
```

**Structure Decision**: Introduce a dedicated `tenants` app to own the `Client`/`Domain`
models and provisioning logic, keeping `documents` app clean of tenant-management concerns.
The `users` app retains `Role`/`Permission` as public-schema shared models.

## Camunda Multi-Tenancy (Process Orchestration Layer)

### Context

DB-level isolation (this feature, above) does not reach the process-orchestration layer.
Camunda 8 (Zeebe) drives the document pipeline as an optional execution path — gated behind
the `camunda` profile in `docuparse-project/docker-compose.yml`, alongside the default
in-process `ThreadPoolExecutor` path in `documents/services/processing_queue.py` (already
tenant-safe: it captures `connection.tenant` from the request thread and re-applies it in the
worker thread). The Zeebe path is a separate, standalone service —
`docuparse-project/camunda-workers` — that receives jobs from Zeebe and calls back into
`backend-core` over HTTP using the shared `DOCUPARSE_INTERNAL_SERVICE_TOKEN`.

Two gaps exist today:

1. `docuparse-project/bpmn/flow.bpmn` only maps `=tenantId → tenant_id` on `Task_Ingestion`
   and `Task_ERP`. `Task_OCR`, `Task_Layout`, and `Task_Extraction` never receive it.
2. `camunda-workers/src/workers/_http.py`'s `core_client()`/`ocr_client()`/etc. only set the
   `Authorization: Bearer <token>` header (`_auth_headers()`). They never set `X-Tenant`, which
   `JWTTenantMiddleware._resolve_slug` (`backend-core/tenants/middleware.py:59-73`) requires for
   any request authenticated with the internal service token — it raises `SuspiciousOperation`
   if the header is absent.

Together, once tenant enforcement is strict, every Camunda-driven OCR/layout/extraction call
fails. This section closes that gap so the Camunda path can be safely enabled in a
multi-tenant deployment.

### Decision: application-level tenant isolation, not Zeebe's native multi-tenancy

Zeebe 8.6 (the version pinned in `docker-compose.yml`) ships engine-level multi-tenancy, but it
requires Camunda Identity + OIDC — not part of this stack, which uses an insecure gRPC channel
(`create_insecure_channel`) with no Identity/Keycloak service. Adopting it would mean standing
up Identity, switching `pyzeebe` to an OAuth credentials provider, and provisioning a service
account per tenant — a disproportionate lift for the current scale (tens of tenants, one
self-managed cluster). Instead, tenant isolation at this layer is enforced the same way it
already is at the HTTP layer: a trusted `tenant_id` carried as data (process variable / header),
validated by the receiving service, not by the engine.

**Revisit** native Zeebe multi-tenancy only if Identity is adopted for an unrelated reason
(e.g., SSO).

### Required changes

1. **BPMN** (`docuparse-project/bpmn/flow.bpmn`): add `=tenantId → tenant_id` to the
   `zeebe:ioMapping` of `Task_OCR`, `Task_Layout`, `Task_Extraction`, and `Task_HumanVal`.
2. **`camunda-workers`**: every task handler in `src/workers/*.py` gains a `tenant_id: str`
   parameter; the client factories in `src/workers/_http.py` accept `tenant_id` and set
   `X-Tenant: <tenant_id>` alongside the bearer token on every request.
3. **Fail closed**: a Zeebe job arriving with a missing/blank `tenant_id` MUST fail the job
   (non-retryable BPMN error), never fall back to a default schema or omit the header.
4. **Provenance**: `tenant_id` MUST be seeded into a process instance only by a trusted,
   tenant-authenticated caller at process-start time, and MUST NOT be accepted as ad hoc input
   further down the flow. Nothing in `backend-core` currently starts Zeebe process instances —
   only the manual `camunda-workers/scripts/start_process.py` CLI does — so this is a dependency
   flag for whichever future feature wires production channels (email/WhatsApp) into Zeebe.
5. **Human task isolation (Tasklist)**: `Task_HumanVal`'s `candidateGroups="operators"` is a
   single shared group today — any operator, of any tenant, can see and claim any tenant's
   review task. Change to a tenant-derived FEEL expression, e.g.
   `candidateGroups="=\"operators-\" + tenantId"`, and provision operator group membership per
   tenant wherever Tasklist users are managed.
6. **Operate/Tasklist admin UIs**: neither supports per-tenant filtering without Identity;
   accept this as an operational risk and restrict access to internal ops staff only — do not
   expose either UI to tenant end users.
7. **Process definition stays single/shared**: do not deploy per-tenant copies of
   `docuparse-pipeline` — only instance *data* needs isolation, not the process model.

### Testing

- Integration test: start two process instances (tenant A, tenant B) concurrently through the
  full pipeline; assert every worker→`backend-core` call carries the correct `X-Tenant` header
  and only ever touches its own tenant's schema.
- Unit test: a job payload with missing/blank `tenant_id` is rejected by each worker before any
  `backend-core` call is attempted.

### Constitution Check (addendum)

| Principle | Assessment |
|-----------|------------|
| **I. Security** | ✅ CRITICAL — `camunda-workers` currently calls `backend-core` without `X-Tenant`, which `JWTTenantMiddleware` will reject once tenant enforcement is strict; closing this is required before the Camunda path can run safely in a multi-tenant deployment |

### Project Structure (addendum)

```text
docuparse-project/
├── bpmn/
│   └── flow.bpmn                     # add tenant_id io-mapping to OCR/Layout/Extraction/
│                                      # HumanVal tasks; tenant-derived candidateGroups
└── camunda-workers/
    └── src/
        ├── workers/
        │   ├── _http.py              # client factories accept tenant_id, set X-Tenant
        │   ├── ocr.py                # tenant_id param threaded through
        │   ├── layout.py
        │   ├── extraction.py
        │   └── validation.py
        └── tests/
            └── test_tenant_propagation.py   # NEW
```

## Complexity Tracking

> No constitution violations require justification.
