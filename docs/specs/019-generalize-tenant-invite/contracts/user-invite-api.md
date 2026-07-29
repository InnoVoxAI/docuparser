# Contract: User Invite API

**Feature**: `019-generalize-tenant-invite` | **Date**: 2026-07-29

Todos os endpoints seguem o envelope padrão já usado em toda a API (mesmo formato do contrato da 017):
```json
{ "data": <payload>, "error": null | { "code": "...", "detail": "..." }, "meta": {} }
```

---

## POST /api/users/ (alterado)

Convida um novo usuário para o tenant do administrador autenticado. **Deixa de exigir senha** — o usuário define a própria senha ao ativar o convite recebido por email (mesmo padrão de `POST /api/admin/tenants/`, feature 017).

**Authentication**: JWT — caller must have `users.manage` permission (inalterado; `tenantAdmin` e `admin` têm essa permissão). O tenant-alvo é `request.tenant`, resolvido do claim JWT (inalterado) — **corrige** o bug pré-existente em que o tenant era sempre `Tenant.objects.first()` (ver [[research.md]] R3).

### Request

```json
{
  "name": "Maria Silva",
  "email": "maria.silva@acme.com",
  "role_id": "8f14e45f-ceea-467e-adde-3fb5f2b0e6a1"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | yes | 1–150 chars (inalterado) |
| `email` | string | yes | formato de email válido; não pode já existir como `username` de outro usuário (inalterado) |
| `role_id` | UUID | yes | deve existir e ter `is_platform_role=False` — **novo**: papéis de plataforma não podem ser atribuídos por convite de tenant admin |
| ~~`password`~~ | — | — | **removido** — não existe mais campo de senha nesta requisição |

### Response 201 Created

```json
{
  "data": {
    "id": 42,
    "name": "Maria Silva",
    "email": "maria.silva@acme.com",
    "is_active": true,
    "role": { "id": "8f14e45f-ceea-467e-adde-3fb5f2b0e6a1", "name": "operator", "is_platform_role": false }
  },
  "error": null,
  "meta": { "invite_sent": true }
}
```

`data` mantém o formato de `UserListSerializer` já usado hoje. `meta.invite_sent` segue o mesmo padrão de `meta.admin_invite_sent` da 017 — indica se o envio do email foi disparado sem exceção, não necessariamente entregue.

### Response 400 Bad Request (role de plataforma selecionada)

```json
{
  "data": null,
  "error": { "code": "VALIDATION_ERROR", "detail": { "role_id": ["Esta role não pode ser atribuída por convite de tenant admin."] } },
  "meta": {}
}
```

### Response 409 Conflict (email já em uso — inalterado)

```json
{
  "data": null,
  "error": { "code": "USER_EXISTS", "detail": "E-mail 'maria.silva@acme.com' já está em uso." },
  "meta": {}
}
```

### Response 500 Internal Server Error (falha ao enviar o convite — mesmo padrão da 017)

```json
{
  "data": null,
  "error": { "code": "INVITE_DELIVERY_FAILED", "detail": "Usuário criado, mas o convite não pôde ser enviado. Use o reenvio de convite." },
  "meta": {}
}
```

O usuário e o `UserProfile` **já foram criados** neste ponto (mesma política de não-rollback da 017) — o tenant admin usa o endpoint de reenvio abaixo.

---

## POST /api/users/{user_id}/invites/resend/ (novo)

Gera um novo convite de ativação para um usuário convidado específico do tenant, invalidando qualquer convite `PENDING` anterior. Generaliza `POST /api/admin/tenants/{slug}/invites/resend/` (017, que continua existindo e passa a ser internamente um caso particular desta mesma lógica — ver [[research.md]] R2), mas mirando um usuário específico em vez de "o admin do tenant".

**Authentication**: JWT — caller must have `users.manage` permission. `user_id` deve pertencer a um `UserProfile` do mesmo `request.tenant` do chamador — caso contrário, 404 (não revela se o usuário existe em outro tenant).

### Request

Sem corpo.

### Response 200 OK

```json
{
  "data": { "email": "maria.silva@acme.com", "expires_at": "2026-07-30T12:00:00Z" },
  "error": null,
  "meta": {}
}
```

### Response 404 Not Found

```json
{
  "data": null,
  "error": { "code": "USER_NOT_FOUND", "detail": "Usuário não encontrado neste tenant." },
  "meta": {}
}
```

### Response 409 Conflict (usuário já ativou a conta)

```json
{
  "data": null,
  "error": { "code": "USER_ALREADY_ACTIVE", "detail": "Este usuário já ativou a conta." },
  "meta": {}
}
```

---

## POST /api/admin/tenants/invites/{token}/activate/ (reaproveitado, sem alteração)

Mesmo endpoint da feature 017 (`tenants/views.py::invite_activate_view`) — nenhuma rota nova, nenhuma alteração de contrato. Já funciona para qualquer `Invite` (renomeado de `TenantAdminInvite`, ver [[data-model.md]]) independentemente do papel atribuído ao usuário convidado, porque a lógica de ativação nunca leu nem gravou papel — só valida o token e define a senha. Ver [[research.md]] R6.

---

## Endpoints inalterados (apenas o model interno mudou de nome)

- `POST /api/admin/tenants/{slug}/invites/resend/` (017) — contrato de request/response idêntico; internamente passa a chamar a versão generalizada de reenvio com o `user_id` do admin do tenant.
- `POST /api/admin/tenants/` (017) — inalterado; internamente passa a criar um `Invite` em vez de `TenantAdminInvite`.
