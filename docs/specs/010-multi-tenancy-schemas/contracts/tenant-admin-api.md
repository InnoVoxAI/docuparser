# Contract: Tenant Admin API

**Feature**: `010-multi-tenancy-schemas` | **Date**: 2026-06-30

All endpoints follow the standard API envelope:
```json
{ "data": <payload>, "error": null | { "code": "...", "detail": "..." }, "meta": {} }
```

---

## POST /api/admin/tenants/

Provisions a new tenant: creates the PostgreSQL schema, runs migrations, and seeds default
Role + Permission records.

**Authentication**: JWT — caller must have `tenants.manage` permission (superuser/admin only).

### Request

```json
{
  "slug": "acme",
  "name": "ACME Corporation"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `slug` | string | yes | 1–50 chars; `[a-z0-9-]` only; must be unique |
| `name` | string | yes | 1–255 chars |

### Response 201 Created

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "slug": "acme",
    "name": "ACME Corporation",
    "schema_name": "tenant_acme",
    "is_active": true,
    "created_at": "2026-06-30T12:00:00Z"
  },
  "error": null,
  "meta": {}
}
```

### Response 409 Conflict (duplicate slug)

```json
{
  "data": null,
  "error": { "code": "TENANT_EXISTS", "detail": "A tenant with slug 'acme' already exists." },
  "meta": {}
}
```

### Response 500 Internal Server Error (schema creation failed)

```json
{
  "data": null,
  "error": { "code": "SCHEMA_CREATION_FAILED", "detail": "Schema creation failed; rollback complete." },
  "meta": {}
}
```

---

## GET /api/admin/tenants/

Lists all tenants (for admin dashboards).

**Authentication**: JWT — `tenants.manage` permission required.

### Response 200 OK

```json
{
  "data": [
    {
      "id": "550e8400-...",
      "slug": "acme",
      "name": "ACME Corporation",
      "schema_name": "tenant_acme",
      "is_active": true,
      "created_at": "2026-06-30T12:00:00Z"
    }
  ],
  "error": null,
  "meta": { "count": 1 }
}
```

---

## PATCH /api/admin/tenants/{slug}/

Update tenant metadata or activation status.

**Authentication**: JWT — `tenants.manage` permission required.

### Request (partial update — all fields optional)

```json
{
  "name": "ACME Corp (updated)",
  "is_active": false
}
```

### Response 200 OK

Returns the updated tenant object (same shape as POST 201).

### Response 403 Forbidden (deactivating last active tenant)

```json
{
  "data": null,
  "error": { "code": "LAST_TENANT", "detail": "Cannot deactivate the only active tenant." },
  "meta": {}
}
```

---

## POST /api/auth/login/ (updated)

Unchanged endpoint signature; updated response to include `tenant` in the JWT payload.

### Response 200 OK

```json
{
  "data": {
    "access": "<JWT with tenant claim>",
    "refresh": "<refresh token>"
  },
  "error": null,
  "meta": {}
}
```

**JWT access token payload** (decoded):
```json
{
  "token_type": "access",
  "user_id": 42,
  "tenant": "acme",
  "exp": 1234567890
}
```

---

## Error Codes Reference

| Code | HTTP Status | When |
|------|-------------|------|
| `TENANT_EXISTS` | 409 | Slug already taken on POST |
| `TENANT_NOT_FOUND` | 404 | Slug not found on PATCH |
| `TENANT_INACTIVE` | 403 | JWT tenant is deactivated |
| `SCHEMA_CREATION_FAILED` | 500 | PostgreSQL schema creation failed |
| `MISSING_TENANT_CLAIM` | 401 | JWT has no `tenant` field |
| `INVALID_TENANT_HEADER` | 401 | `X-Tenant` header missing or unknown (service token path) |
