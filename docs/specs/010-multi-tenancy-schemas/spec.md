# Feature Specification: Multi-Tenancy — PostgreSQL Schema-per-Tenant

**Feature Branch**: `010-multi-tenancy-schemas`

**Created**: 2026-06-30

**Status**: Draft

**Input**: "We need to add multi-tenancy to the django side of the app using the same db, separate schemas approach. Each tenant has their own access to the docuparser platform"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Tenant Data Isolation (Priority: P1)

An operator from Tenant A logs in and can only see their company's documents, settings, and
extraction results. No cross-tenant data leakage is possible, regardless of query parameters
or API misuse.

**Why this priority**: This is the core invariant of multi-tenancy. Without it, all other
stories are unsafe to ship.

**Independent Test**: Create two tenants with documents, authenticate as Tenant A's user,
verify zero Tenant B documents appear in any list or detail endpoint.

**Acceptance Scenarios**:

1. **Given** two tenants (A and B) each with 3 documents, **When** an authenticated Tenant A
   user calls `GET /api/documents/`, **Then** only Tenant A's 3 documents are returned.
2. **Given** a valid Tenant A JWT, **When** the user requests a Tenant B document UUID directly,
   **Then** the API returns 404 (not 403, to avoid leaking existence).
3. **Given** a request with an invalid or missing tenant context, **When** any protected endpoint
   is called, **Then** the API returns 401.

---

### User Story 2 — Tenant Provisioning (Priority: P1)

An administrator can create a new tenant (organisation), which automatically provisions an
isolated PostgreSQL schema and seeds the default configuration (roles, permissions, email
settings).

**Why this priority**: Without provisioning, no new tenants can onboard.

**Independent Test**: Call the tenant creation API, then verify the PostgreSQL schema was
created, default data was seeded, and a superuser profile can authenticate against that tenant.

**Acceptance Scenarios**:

1. **Given** a POST to `POST /api/admin/tenants/` with `{slug, name}`, **When** the request
   succeeds, **Then** a PostgreSQL schema named `tenant_<slug>` exists and contains all
   tenant-scoped tables.
2. **Given** a duplicate slug, **When** the POST is attempted, **Then** the API returns 409 Conflict.
3. **Given** a newly provisioned tenant, **When** the tenant schema is inspected, **Then** it
   contains Role, Permission (seeded), and empty Document/Settings tables.

---

### User Story 3 — JWT-Based Tenant Resolution (Priority: P1)

When a user authenticates via `/api/auth/login/`, the JWT access token encodes the tenant slug.
Every subsequent request automatically routes to the correct schema without requiring any
additional HTTP header.

**Why this priority**: Tenant resolution is the mechanism that makes P1 stories work.

**Independent Test**: Authenticate as a user belonging to Tenant A, decode the JWT, confirm
`tenant` claim is present, make any API call, confirm it hits the correct schema.

**Acceptance Scenarios**:

1. **Given** a user with `UserProfile.tenant.slug = "acme"`, **When** they POST credentials to
   `/api/auth/login/`, **Then** the returned JWT contains `{"tenant": "acme"}` in the payload.
2. **Given** a valid JWT with `tenant: "acme"`, **When** any protected API endpoint is called,
   **Then** the database connection uses the `tenant_acme` PostgreSQL schema.
3. **Given** a JWT whose tenant claim references a non-existent schema, **When** a request is
   made, **Then** the API returns 401 with a clear error.

---

### User Story 4 — Tenant-Scoped Settings (Priority: P2)

Each tenant manages their own OCR settings, integration settings, email settings, schema
configs, and layout configs independently. Changes by one tenant do not affect any other tenant.

**Why this priority**: Operational independence between tenants; required for SaaS billing/feature
differentiation later.

**Independent Test**: Update OCR settings for Tenant A, verify Tenant B OCR settings are
unchanged.

**Acceptance Scenarios**:

1. **Given** Tenant A sets `digital_pdf_engine = "docling"`, **When** Tenant B reads their OCR
   settings, **Then** Tenant B's settings are unaffected (remain at their own value).
2. **Given** Tenant A's `LayoutConfig` table, **When** it is queried, **Then** only layouts
   belonging to Tenant A's schema are returned.

---

### Edge Cases

- What happens when a superuser (is_staff) JWT is issued without a tenant claim?
  → Staff users bypass schema routing and operate on the public schema (admin use only).
- What happens if schema creation fails mid-provisioning?
  → Rollback: drop the partially created schema and return 500 with a clear message.
- What happens when a tenant is deactivated (`is_active = False`)?
  → All authenticated requests for that tenant receive 403 until reactivated.
- How does the internal service token (used by OCR/LangExtract services) identify its tenant?
  → Internal calls MUST include an `X-Tenant` header; the middleware resolves the schema
    from this header when `request.auth == "service_token"`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST enforce complete data isolation between tenants using PostgreSQL
  schemas (one schema per tenant named `tenant_<slug>`).
- **FR-002**: System MUST embed the tenant slug in the JWT access token at login time.
- **FR-003**: A middleware MUST resolve the active tenant schema from the JWT claim on every
  request before any database query is executed.
- **FR-004**: System MUST expose a tenant provisioning endpoint (`POST /api/admin/tenants/`)
  that creates the PostgreSQL schema and runs tenant-scoped migrations automatically.
- **FR-005**: Internal service-to-service calls MUST resolve the tenant via the `X-Tenant`
  HTTP header when using the static service token.
- **FR-006**: The `Tenant` model, `UserProfile`, `Role`, and `Permission` MUST remain in the
  `public` schema (shared tables).
- **FR-007**: All document-processing models (`Document`, `ExtractionResult`, etc.) MUST live
  in per-tenant schemas, with no `tenant` FK column on those models.
- **FR-008**: A management command MUST exist to migrate existing shared-schema data into the
  correct per-tenant schemas.
- **FR-009**: Deactivated tenants (`Tenant.is_active = False`) MUST receive 403 on all
  authenticated API calls.
- **FR-010**: The system MUST seed default `Role` and `Permission` records into each newly
  provisioned tenant schema.

### Key Entities

- **Tenant** (public schema): Organisation record. Slug becomes the PostgreSQL schema prefix.
- **Domain** (public schema): django-tenants routing table mapping hostname/slug to Tenant.
- **UserProfile** (public schema): Links `auth.User` to a `Tenant`; establishes the tenant
  claim embedded in the JWT.
- **Document, ExtractionResult, ValidationDecision, etc.** (per-tenant schema): All
  document-processing entities move to per-tenant schemas; `tenant` FK is removed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero cross-tenant data leakage in automated integration tests (100% isolation
  verified by querying each tenant's endpoint with the other tenant's JWT).
- **SC-002**: New tenant provisioning completes in under 5 seconds (schema creation + migration
  + seed).
- **SC-003**: API response times for protected endpoints remain within the 200 ms p95 budget
  (constitution §IV) after schema-routing middleware is added.
- **SC-004**: All existing unit and integration tests pass after the refactor (no regressions).
- **SC-005**: The migration command successfully moves existing single-tenant data to the
  `tenant_<slug>` schema with zero data loss.

## Assumptions

- The application is currently single-tenant in practice (one Tenant row in the DB), making
  the migration command a one-shot operation without complex conflict resolution.
- Subdomains are **not** used for tenant routing; JWT claims are the sole routing mechanism.
  This avoids infra changes to DNS/reverse proxy.
- The internal service token used by OCR/LangExtract services will be augmented with an
  `X-Tenant` HTTP header — no token-per-tenant strategy is needed at this stage.
- `django-tenants` (latest stable, compatible with Django 5.x) is the chosen library.
- The `auth.User` table remains in the public schema; a user may theoretically belong to
  multiple tenants via multiple `UserProfile` rows, but the JWT targets one tenant per session.
- Django Admin is out of scope for multi-tenant routing in this feature.
