# Data Model: Multi-Tenancy — PostgreSQL Schema-per-Tenant

**Branch**: `010-multi-tenancy-schemas` | **Date**: 2026-06-30

---

## Schema Layout

```
PostgreSQL database: docuparse
│
├── public (shared schema)
│   ├── django_tenants_tenant  ← Tenant (Client)
│   ├── django_tenants_domain  ← Domain
│   ├── auth_user
│   ├── auth_group
│   ├── django_content_type
│   ├── django_session
│   ├── token_blacklist_*      ← simplejwt blacklist tables
│   ├── documents_userprofile
│   ├── users_role
│   ├── users_permission
│   └── users_role_permissions
│
└── tenant_<slug> (per tenant, one per org)
    ├── documents_document
    ├── documents_documentevent
    ├── documents_extractionresult
    ├── documents_extractionfieldversion
    ├── documents_validationdecision
    ├── documents_erpintegrationattempt
    ├── documents_integrationsettings
    ├── documents_ocrsettings
    ├── documents_emailsettings
    ├── documents_schemaconfig
    └── documents_layoutconfig
```

---

## Public Schema Models

### Tenant (updated — now `TenantMixin`)

Inherits `django_tenants.models.TenantMixin`. The `schema_name` field is the PostgreSQL
schema identifier; `slug` is the human-facing identifier embedded in JWT claims.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | unchanged |
| `schema_name` | CharField(63), unique | NEW — `"tenant_" + slug`; used by django-tenants |
| `slug` | SlugField, unique | unchanged — JWT claim value |
| `name` | CharField(255) | unchanged |
| `is_active` | BooleanField | unchanged |
| `created_at` | DateTimeField | unchanged |
| `updated_at` | DateTimeField | unchanged |
| `auto_create_schema` | class attr = True | tells django-tenants to run migrations on save() |

**Migration note**: `schema_name` is a new required field. A data migration populates it as
`"tenant_" + slug` for all existing rows before the `TenantMixin` constraints are applied.

---

### Domain (new)

Maps request identifiers to tenants. Used by django-tenants middleware; even in JWT mode we
need at least one `Domain` row per tenant so the framework's provisioning lifecycle works.

| Field | Type | Notes |
|-------|------|-------|
| `id` | BigAutoField (PK) | django-tenants default |
| `tenant` | FK → Tenant | the owning tenant |
| `domain` | CharField(253), unique | e.g., `"tenant-acme.internal"` or `"acme"` |
| `is_primary` | BooleanField | one primary domain per tenant |

---

### UserProfile (updated — moved to `public` schema)

Previously lived in `documents` app (and thus in per-tenant schemas). Now explicitly placed
in `SHARED_APPS` so it resolves the `user → tenant` mapping before schema routing occurs.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | unchanged |
| `user` | OneToOneFK → auth.User | unchanged |
| `tenant` | FK → Tenant | unchanged — the public-schema Tenant |
| `role_ref` | FK → users.Role | nullable; Role stays in `public` schema |
| `created_at` | DateTimeField | unchanged |
| `updated_at` | DateTimeField | unchanged |

**Constraint**: `UniqueConstraint(fields=["tenant", "user"])` unchanged.

---

### Role, Permission (unchanged — public schema)

No model changes. Both move to `SHARED_APPS` so they live in the public schema and are
accessible before schema routing. All tenants share the same Role/Permission definitions.

---

## Per-Tenant Schema Models (changes only)

All per-tenant models retain their existing fields. The only change across all of them is:

**REMOVED**: `tenant = models.ForeignKey(Tenant, ...)` — replaced by schema isolation.

**REMOVED indexes**:
- `Index(fields=["tenant", "status"])` → replaced by `Index(fields=["status"])`
- `Index(fields=["tenant", "received_at"])` → replaced by `Index(fields=["received_at"])`
- `Index(fields=["tenant", "event_type"])` → replaced by `Index(fields=["event_type"])`

**REMOVED constraints** referencing tenant (in Document, DocumentEvent, etc.) — per-schema
isolation makes these redundant.

### Document (updated)

```python
class Document(TimeStampedModel):
    # REMOVED: tenant = FK(Tenant)
    id = models.UUIDField(primary_key=True, ...)
    status = models.CharField(...)
    channel = models.CharField(...)
    file_uri = models.CharField(...)
    # ... all other fields unchanged ...

    class Meta:
        indexes = [
            models.Index(fields=["status"]),          # was ["tenant", "status"]
            models.Index(fields=["received_at"]),     # was ["tenant", "received_at"]
        ]
```

### DocumentEvent (updated)

```python
class DocumentEvent(TimeStampedModel):
    # REMOVED: tenant = FK(Tenant)
    # ... all other fields unchanged ...

    class Meta:
        indexes = [
            models.Index(fields=["event_type"]),      # was ["tenant", "event_type"]
            models.Index(fields=["document", "occurred_at"]),  # unchanged
        ]
```

### IntegrationSettings, OCRSettings, EmailSettings (updated)

```python
# REMOVED on all three:
# tenant = models.OneToOneField(Tenant, ...)
# These become implicit singletons per schema (enforce via constraint or application logic).
```

Each settings model becomes a natural singleton within its tenant schema. The `OneToOneField`
on `Tenant` is replaced by a simple `UniqueConstraint` on no fields (or a single-row
enforcement in the service layer).

### SchemaConfig, LayoutConfig (updated)

```python
# REMOVED on both:
# tenant = models.ForeignKey(Tenant, ...)
# tenant-scoping constraints (UniqueConstraint including "tenant" field)
```

`SchemaConfig` constraint becomes `UniqueConstraint(fields=["schema_id", "version"])`.
`LayoutConfig` constraint becomes `UniqueConstraint(fields=["layout", "document_type"])`.

---

## JWTTenantMiddleware — Schema Resolution Flow

```
Request arrives
    │
    ▼
JWTTenantMiddleware.get_tenant(request)
    │
    ├─ auth == "service_token"?
    │   └─ Read X-Tenant header → look up Tenant.objects.get(slug=header_value)
    │
    └─ JWT present?
        └─ Decode token (without full validation — just claims)
            └─ claim["tenant"] → Tenant.objects.get(slug=claim, is_active=True)
                │
                ├─ Found → set connection.schema_name = tenant.schema_name
                │           SET search_path TO tenant_<slug>, public
                │
                └─ Not found / inactive → raise SuspiciousOperation (→ 401)

Request continues with ORM targeting tenant_<slug> schema
```

---

## JWT Token Payload (updated)

```json
{
  "token_type": "access",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "...",
  "user_id": 42,
  "tenant": "acme"
}
```

The `tenant` claim is injected by overriding `simplejwt`'s `TokenObtainPairSerializer`:

```python
class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        profile = user.docuparse_profile  # public-schema UserProfile
        token["tenant"] = profile.tenant.slug
        return token
```

---

## Settings Configuration

```python
# settings.py additions

SHARED_APPS = [
    "django_tenants",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "tenants",   # NEW app: Tenant (Client), Domain, UserProfile
    "users",     # Role, Permission
]

TENANT_APPS = [
    "documents",  # all per-tenant operational models
]

INSTALLED_APPS = list(SHARED_APPS) + list(TENANT_APPS)

TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

MIDDLEWARE = [
    "tenants.middleware.JWTTenantMiddleware",  # MUST be first (before auth)
    "django.middleware.security.SecurityMiddleware",
    # ... rest unchanged ...
]

DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]
```

---

## Migration Sequence

### Step 1 — Install django-tenants, create `tenants` app
New migrations in `tenants/` app. No changes to existing migrations yet.

### Step 2 — Data migration: populate `schema_name`, create `Domain` rows
```
documents/migrations/XXXX_populate_schema_name.py  ← RunPython migration
```

### Step 3 — Run shared migrations
```bash
python manage.py migrate_schemas --shared
```
Creates public schema tables for SHARED_APPS.

### Step 4 — Provision existing tenant schemas
```bash
python manage.py migrate_to_schemas --dry-run
python manage.py migrate_to_schemas
```
Copies data from shared `documents_*` tables into per-tenant schemas.

### Step 5 — Remove `tenant` FK from per-tenant models
Separate migration per model, drop FK columns and corresponding indexes.

### Step 6 — Run full schema migration
```bash
python manage.py migrate_schemas
```
Applies Step 5 migrations to all tenant schemas.
