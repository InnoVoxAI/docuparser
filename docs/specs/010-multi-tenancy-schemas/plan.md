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

## Complexity Tracking

> No constitution violations require justification.
