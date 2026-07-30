# Data Model: Convite Direto de Usuários por Tenant Admin

## Overview

Esta feature não introduz nenhum modelo novo. Ela renomeia `TenantAdminInvite` → `Invite` (ver [[research.md]] R1) e generaliza o código que o usa em `tenants/invites.py`. `Tenant`, `UserProfile`, `Role`, `Permission` (`docuparse-project/backend-core/tenants/models.py`, `users/models.py`) permanecem inalterados na forma.

## Entities

### Invite (renomeado de `TenantAdminInvite`)

App: `tenants` (schema público, `SHARED_APPS` — inalterado).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID (PK, default `uuid4`) | Inalterado. |
| `user` | FK → `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`, `related_name="invites"` (renomeado de `admin_invites`) | O usuário convidado, já criado sem senha utilizável, com `UserProfile.role_ref` já atribuído ao papel do convite. |
| `tenant` | FK → `tenants.Tenant`, `on_delete=CASCADE`, `related_name="invites"` (renomeado de `admin_invites`) | Inalterado em propósito — permite consultar/expirar convites por tenant sem join adicional. |
| `token_hash` | `CharField(max_length=128, unique=True, db_index=True)` | Inalterado. |
| `status` | `CharField(choices=PENDING/USED/INVALIDATED, default=PENDING)` | Inalterado. |
| `expires_at` | `DateTimeField` | Inalterado — mesmo `settings.TENANT_ADMIN_INVITE_TTL_HOURS` (nome de setting mantido; renomear a env var é opcional e não obrigatório para esta feature). |
| `used_at` | `DateTimeField(null=True, blank=True)` | Inalterado. |
| `created_at` / `updated_at` | herdado de `TimeStampedModel` | Inalterado. |

**O que muda de fato**: nenhum campo. Migração é só `RenameModel("TenantAdminInvite", "Invite")` + `RenameField`/atualização dos `related_name` (`admin_invites` → `invites`, para não sugerir que só admins têm convites). Todo o restante do código que lê/escreve `TenantAdminInvite` passa a importar `Invite`.

**Validações / regras de negócio** (inalteradas de 017, ver [[../017-tenant-admin-onboarding/data-model.md|data-model.md da 017]]):

- No máximo um convite `PENDING` por `user` — reforçado na camada de serviço (`invites.py`), não como constraint de banco.
- `token_hash` gerado a partir de `secrets.token_urlsafe(32)`, hasheado com SHA-256; token em claro só trafega no email e na URL.
- Convite só é válido se `status == PENDING` e `expires_at > now()`.

**Estados** (inalterado):

```
PENDING --(usado com sucesso)--> USED
PENDING --(expiração natural, detectada em leitura)--> tratado como expirado
PENDING --(reenvio solicitado)--> INVALIDATED
```

### UserProfile (existente — sem alteração de schema)

`role_ref` já é onde o papel do usuário convidado vive — **não é adicionado a `Invite`**. Isso é o que torna o rename suficiente em vez de exigir um campo `role`/`invite_type`: o papel é decidido e persistido em `UserProfile` no momento em que o convite é emitido (`create_admin_invite`/generalização `create_invite`), exatamente como já acontece hoje para o admin.

### User (Django `auth.User` — sem alteração)

Inalterado. Continua sendo criado com `is_active=True` e `set_unusable_password()` até a ativação, para qualquer papel (admin ou usuário comum).

## Relationships

```
Tenant 1───* UserProfile *───1 User 1───* Invite
                                  │
                                  └── User.docuparse_profile → UserProfile (role_ref = papel do convite)
```

## Migration Notes

- Uma única migração no app `tenants`: `RenameModel` (`TenantAdminInvite` → `Invite`), ajuste de `related_name` em `user`/`tenant` (`admin_invites` → `invites`). Roda apenas no schema público (`tenants` é `SHARED_APPS`) — sem necessidade de `migrate_schemas --tenant` por schema de cada cliente.
- Nenhuma migração de dados (nenhum campo novo, nenhum valor a recalcular) — é puramente estrutural (rename de tabela/FKs).
