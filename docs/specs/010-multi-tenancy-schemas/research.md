# Research: Multi-Tenancy — PostgreSQL Schema-per-Tenant

**Feature**: `010-multi-tenancy-schemas` | **Date**: 2026-06-30

---

## Decision 1: Library — `django-tenants`

**Decision**: Use `django-tenants` v3.x (latest stable).

**Rationale**: django-tenants is the only actively maintained library with first-class
PostgreSQL schema switching built into Django's ORM routing. It provides:
- `TenantMixin` base class for the Client model (our `Tenant` equivalent)
- `SHARED_APPS` / `TENANT_APPS` settings split that controls which models land in `public`
  vs per-tenant schemas
- Custom migration commands (`migrate_schemas`) that handle both schema types
- First-class test utilities (`TenantTestCase`, `FastTenantTestCase`, `TenantClient`)
- Django 5.0.1 is within the supported range (django-tenants supports `< 5.2`)

**Alternatives considered**:
- `django-tenant-schemas` — archived/unmaintained; django-tenants is its maintained fork.
- Custom `search_path` middleware without a library — feasible but requires reimplementing
  migration routing, test utilities, and schema-creation lifecycle; not worth it.
- Row-Level Security (PostgreSQL RLS) — enforces isolation at the DB level but requires
  complex policy management and doesn't remove the `tenant` FK columns; doesn't align with
  the user's "separate schemas" requirement.

---

## Decision 2: Tenant Resolution Strategy — JWT Claim

**Decision**: Resolve the active schema from the `tenant` claim in the JWT access token.
Subclass `BaseTenantMiddleware` and override `get_tenant(request)` to decode the claim.

**Rationale**: The project has no subdomain routing (requests arrive at a single host),
making the default django-tenants `TenantMiddleware` (domain-matching) inapplicable.
JWT-based resolution is the natural fit because:
1. Users already authenticate with JWT (djangorestframework-simplejwt).
2. The `UserProfile` model already links `auth.User` to a `Tenant`.
3. No DNS/reverse-proxy changes are required.

**Critical ordering constraint**: The `JWTTenantMiddleware` MUST appear in `MIDDLEWARE`
before `AuthenticationMiddleware` (and before any DRF authentication) because the schema
must be set before any ORM query executes.

**Gotcha resolved**: JWT tokens are global by default. The middleware must validate that the
JWT's `tenant` claim matches a live Tenant row in the public schema. An unknown or inactive
tenant slug returns 401 immediately, before the token signature is fully validated.

**Alternatives considered**:
- `X-Tenant-Slug` HTTP header — simpler but requires clients to know and send the slug; JWT
  is already the auth mechanism, so embedding the slug there is cleaner.
- Subdomain routing — would require DNS wildcard + reverse-proxy changes; rejected.

---

## Decision 3: Public vs Tenant Schema Split

**Decision**:

| Schema | Models |
|--------|--------|
| `public` (shared) | `Tenant` (Client), `Domain`, `auth.User`, `UserProfile`, `Role`, `Permission` |
| `tenant_<slug>` | `Document`, `DocumentEvent`, `ExtractionResult`, `ExtractionFieldVersion`, `ValidationDecision`, `ERPIntegrationAttempt`, `IntegrationSettings`, `OCRSettings`, `EmailSettings`, `SchemaConfig`, `LayoutConfig` |

**Rationale**: The `public` schema holds everything needed to resolve a request's tenant
identity (Tenant + UserProfile) and to authenticate a user (auth.User). Once the schema is
resolved, all operational data is isolated in the per-tenant schema with no cross-references
needed.

`UserProfile` stays in public because resolving `user → tenant` requires a public-schema
lookup before the per-tenant schema is set. Moving it to per-tenant schemas would create
a chicken-and-egg problem.

**Implication**: The `tenant` FK on Document, ExtractionResult, etc. is **dropped** — it is
replaced by the implicit PostgreSQL schema isolation.

---

## Decision 4: `Tenant` Model Refactor — `TenantMixin`

**Decision**: Rename the existing `Tenant` model to `Client` (or keep as `Tenant` but
inherit from `TenantMixin`). Add required `schema_name` field (derived from `slug`). Add
the `Domain` model.

**Rationale**: django-tenants requires the Client model to inherit from `TenantMixin`, which
adds `schema_name` and lifecycle hooks (`create_schema()`, `auto_create_schema`). The
existing `slug` field maps naturally to `schema_name` with a `tenant_` prefix.

**Concrete mapping**:
```python
from django_tenants.models import TenantMixin, DomainMixin

class Tenant(TenantMixin, TimeStampedModel):
    schema_name = models.CharField(max_length=63, unique=True)  # "tenant_acme"
    slug = models.SlugField(unique=True)                         # "acme"
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    auto_create_schema = True   # triggers schema + migrations on save()

class Domain(DomainMixin):
    pass  # adds tenant FK + domain + is_primary
```

---

## Decision 5: Data Migration Strategy

**Decision**: Write a management command `migrate_to_schemas` that:
1. Iterates each `Tenant` row in the public schema.
2. Creates the tenant schema via `tenant.create_schema(check_if_exists=True)`.
3. Runs `migrate_schemas --schema=<schema_name>` programmatically to create all tables.
4. Copies rows from the shared tables into the per-tenant schema using raw SQL
   (`INSERT INTO tenant_acme.documents_document SELECT ... FROM public.documents_document WHERE tenant_id = ...`).
5. Drops the `tenant_id` FK column from public tables (or drops the entire public copies
   once data is verified).

**Rationale**: A one-shot management command is the safest approach for an existing
single-tenant production system. It can be dry-run first, then applied. Using raw SQL for
the copy step avoids Django ORM confusion during the transition (when both schemas partially
exist).

**Risk mitigation**: The command MUST:
- Run inside a database transaction per tenant (rollback individual tenant on failure).
- Print row counts before and after for manual verification.
- Accept `--dry-run` and `--tenant-slug` flags for safe iteration.

---

## Decision 6: Internal Service Token + Tenant Header

**Decision**: When `request.auth == "service_token"` (static internal token used by OCR /
LangExtract services), the `JWTTenantMiddleware` falls back to resolving the tenant from the
`X-Tenant` HTTP header instead of a JWT claim.

**Rationale**: Internal services (backend-ocr, langextract-service) call backend-core without
user JWTs. They must still route to the correct tenant schema. An `X-Tenant: <slug>` header
is the simplest extension. The existing `DocuparseAuthentication` class handles the token
validation; the middleware handles the schema routing.

---

## Decision 7: Testing Approach

**Decision**: Use `django_tenants.test.cases.TenantTestCase` for all integration tests that
exercise schema routing. Unit tests for JWT parsing/middleware logic MAY use `SimpleTestCase`.
All `migrate_to_schemas` command tests MUST run against a real PostgreSQL instance.

**Rationale**: `TenantTestCase` creates a real schema per test class (wrapped in a transaction
for cleanup). SQLite cannot be used for any test touching the schema-switching path.

**CI implication**: The `POSTGRES_HOST` env var must be set in CI for schema-routing tests.
A separate `pytest -m "not tenant"` run can use SQLite for the remaining unit tests.
