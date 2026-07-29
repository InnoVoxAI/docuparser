# Contract: Tenant Admin Invite API

**Feature**: `017-tenant-admin-onboarding` | **Date**: 2026-07-29

All endpoints follow the standard API envelope (mesmo padrão de `docs/specs/010-multi-tenancy-schemas/contracts/tenant-admin-api.md`):
```json
{ "data": <payload>, "error": null | { "code": "...", "detail": "..." }, "meta": {} }
```

---

## POST /api/admin/tenants/ (alterado)

Provisiona um novo tenant. Passa a exigir também os dados do administrador; não gera mais email fake nem senha compartilhada.

**Authentication**: JWT — caller must have `tenants.manage` permission (inalterado).

### Request

```json
{
  "slug": "acme",
  "name": "ACME Corporation",
  "admin_name": "Jane Doe",
  "admin_email": "jane.doe@acme.com"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `slug` | string | yes | 1–50 chars; `[a-z0-9-]` only; must be unique (inalterado) |
| `name` | string | yes | 1–255 chars (inalterado) |
| `admin_name` | string | yes | **novo** — 1–255 chars |
| `admin_email` | string | yes | **novo** — formato de email válido; não pode já existir como `username` de outro usuário |

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
  "meta": {
    "admin_invite_sent": true
  }
}
```

`data` mantém o formato atual (`TenantSerializer`) sem alterações — nenhum dado do admin é retornado no payload (nem email, nem qualquer indício do token), evitando vazamento de PII na resposta de uma ação que já é auditável por outros meios. `meta.admin_invite_sent` informa se o envio do email foi disparado com sucesso (não necessariamente entregue — apenas que a chamada ao backend de email não lançou exceção).

### Response 400 Bad Request (admin_email inválido/ausente)

```json
{
  "data": null,
  "error": { "code": "VALIDATION_ERROR", "detail": { "admin_email": ["Enter a valid email address."] } },
  "meta": {}
}
```

Segue o padrão já existente do `TenantCreateSerializer` (mesma resposta de validação da API atual) — apenas com os novos campos incluídos na validação.

### Response 409 Conflict (duplicate slug — inalterado)

```json
{
  "data": null,
  "error": { "code": "TENANT_EXISTS", "detail": "A tenant with slug 'acme' already exists." },
  "meta": {}
}
```

### Response 409 Conflict (admin_email já em uso — novo)

```json
{
  "data": null,
  "error": { "code": "ADMIN_EMAIL_IN_USE", "detail": "E-mail 'jane.doe@acme.com' já está em uso por outra conta." },
  "meta": {}
}
```

### Response 500 Internal Server Error (falha ao enviar o convite)

```json
{
  "data": null,
  "error": { "code": "INVITE_DELIVERY_FAILED", "detail": "Tenant criado, mas o convite não pôde ser enviado. Use o reenvio de convite." },
  "meta": {}
}
```

O tenant e o usuário administrador **já foram criados** neste ponto (rollback não é aplicado só por falha de envio de email — ver Edge Cases do spec); o operador é orientado a usar o endpoint de reenvio abaixo.

---

## POST /api/admin/tenants/{slug}/invites/resend/ (novo)

Gera um novo convite de ativação para o administrador do tenant, invalidando qualquer convite `PENDING` anterior.

**Authentication**: JWT — caller must have `tenants.manage` permission (mesmo nível de `tenant_list_create_view`).

### Request

Sem corpo (o admin do tenant é resolvido a partir do `UserProfile` com `role_ref.name == "admin"` associado ao tenant).

### Response 200 OK

```json
{
  "data": { "admin_email": "jane.doe@acme.com", "expires_at": "2026-07-30T12:00:00Z" },
  "error": null,
  "meta": {}
}
```

### Response 404 Not Found

```json
{
  "data": null,
  "error": { "code": "TENANT_NOT_FOUND", "detail": "No tenant with slug 'acme'." },
  "meta": {}
}
```

(Mesmo formato de erro já usado em `tenant_detail_update_view`/`tenant_users_view`.)

### Response 409 Conflict (admin já ativou a conta)

```json
{
  "data": null,
  "error": { "code": "ADMIN_ALREADY_ACTIVE", "detail": "O administrador deste tenant já ativou a conta." },
  "meta": {}
}
```

---

## POST /api/admin/tenants/invites/{token}/activate/ (novo, público)

Ativa a conta do administrador convidado, definindo sua senha. **Não requer autenticação** — a validade é garantida inteiramente pelo token.

**Authentication**: nenhuma (`authentication_classes([])`, `permission_classes([])`, mesmo padrão de `login_view`/`register_view` em `users/auth_views.py`).

### Request

```json
{
  "password": "uma-senha-forte-o-suficiente"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `password` | string | yes | Sujeita a `AUTH_PASSWORD_VALIDATORS` (ver research.md R6) |

### Response 200 OK

```json
{
  "data": { "email": "jane.doe@acme.com", "tenant_slug": "acme" },
  "error": null,
  "meta": {}
}
```

Não retorna tokens JWT automaticamente — o administrador é redirecionado para a tela de login após ativar a conta (evita acoplar ativação de senha a início de sessão automático, mantendo os dois fluxos independentes e auditáveis separadamente).

### Response 400 Bad Request (senha não atende aos critérios)

```json
{
  "data": null,
  "error": { "code": "VALIDATION_ERROR", "detail": { "password": ["This password is too short. It must contain at least 8 characters."] } },
  "meta": {}
}
```

### Response 404 Not Found (token inexistente)

```json
{
  "data": null,
  "error": { "code": "INVITE_NOT_FOUND", "detail": "Convite inválido." },
  "meta": {}
}
```

### Response 410 Gone (token expirado)

```json
{
  "data": null,
  "error": { "code": "INVITE_EXPIRED", "detail": "Este convite expirou. Solicite um novo ao administrador da plataforma." },
  "meta": {}
}
```

### Response 410 Gone (token já usado)

```json
{
  "data": null,
  "error": { "code": "INVITE_ALREADY_USED", "detail": "Este convite já foi utilizado." },
  "meta": {}
}
```

`INVITE_NOT_FOUND` (404) é usado apenas para token sintaticamente inválido/inexistente no banco; `INVITE_EXPIRED`/`INVITE_ALREADY_USED` (410) são usados para tokens que existiram mas não são mais válidos — a distinção permite ao frontend mostrar "peça um novo convite" apenas nos casos 410, sem confundir com um link malformado.
