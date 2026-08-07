# Data Model: Onboarding do Administrador de Tenant via Convite por Email

## Overview

Esta feature introduz uma entidade nova (`TenantAdminInvite`) e altera o fluxo de criação do usuário administrativo do tenant. Nenhum modelo existente é removido; `Tenant` e `UserProfile` (`docuparse-project/backend-core/tenants/models.py`) permanecem inalterados na forma. `TenantAdminInvite` vive no app `tenants`, que é um `SHARED_APPS` (schema público, `core/settings.py:20-33`) — assim como `Tenant`, `Domain` e `UserProfile` — o que permite que o endpoint de ativação funcione antes de qualquer resolução de schema de tenant, do mesmo jeito que hoje `api/admin/tenants/` já é servido a partir do schema público (`core/urls.py`).

## Entities

### TenantAdminInvite (novo)

App: `tenants` (schema público, mesmo app de `Tenant`/`UserProfile`).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID (PK, default `uuid4`) | Segue o padrão dos demais modelos do app (`Tenant.id`, `UserProfile.id`). |
| `user` | FK → `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`, `related_name="admin_invites"` | O usuário administrador ainda sem senha utilizável. |
| `tenant` | FK → `tenants.Tenant`, `on_delete=CASCADE`, `related_name="admin_invites"` | Redundante com `UserProfile.tenant` mas mantido diretamente para permitir consultar/expirar convites por tenant sem join adicional e para sobreviver caso o `UserProfile` ainda não exista no momento da criação do convite. |
| `token_hash` | `CharField(max_length=128, unique=True, db_index=True)` | SHA-256 hex digest do token gerado (o token em claro **nunca** é persistido — só existe no link enviado por email e na resposta imediata da criação, se aplicável). |
| `status` | `CharField(choices=PENDING/USED/INVALIDATED, default=PENDING)` | `INVALIDATED` cobre tanto expiração observada quanto superação por um reenvio (FR-010). Calculado como "expirado" em tempo de leitura comparando `expires_at` com `now()`, sem exigir um job de limpeza. |
| `expires_at` | `DateTimeField` | `created_at + settings.TENANT_ADMIN_INVITE_TTL` (ver Assumptions do spec — valor configurável, não hardcoded). |
| `used_at` | `DateTimeField(null=True, blank=True)` | Preenchido no momento da ativação bem-sucedida. |
| `created_at` / `updated_at` | herdado de `TimeStampedModel` (mesmo mixin já usado por `Tenant`/`UserProfile`) | |

**Validações / regras de negócio**:

- Unicidade lógica: no máximo um convite com `status=PENDING` por `user` — reforçada na camada de serviço (ao gerar um novo convite para o mesmo usuário, qualquer `PENDING` existente é marcado `INVALIDATED` antes de criar o novo), não como constraint de banco, porque `INVALIDATED`/`USED` devem poder coexistir historicamente com um novo `PENDING`.
- `token_hash` é gerado a partir de `secrets.token_urlsafe(32)` (ou equivalente), hasheado com SHA-256 antes de salvar; o token em claro só trafega no corpo do email e na URL do link.
- Um convite só é válido para ativação se `status == PENDING` **e** `expires_at > now()`. Qualquer outra combinação retorna erro (ver `contracts/`).

**Estados**:

```
PENDING --(usado com sucesso)--> USED
PENDING --(expiração natural, detectada em leitura)--> tratado como expirado (sem transição de status persistida)
PENDING --(reenvio solicitado / novo convite gerado)--> INVALIDATED
```

### Tenant (existente — sem alteração de schema)

`docuparse-project/backend-core/tenants/models.py:18-38`. Nenhum campo novo. Continua sendo criado por `_provision_tenant` com os mesmos `slug`/`name`/`schema_name`.

### UserProfile (existente — sem alteração de schema)

`docuparse-project/backend-core/tenants/models.py:45-72`. Continua ligando `User` ↔ `Tenant` ↔ `Role`. Passa a ser criado com um `User` cujo `email`/`username` é o email real informado no formulário (em vez de `admin@{slug}`), e sem senha utilizável até a ativação (`user.set_unusable_password()` no lugar de `user.set_password(admin_password)`).

### User (Django `auth.User`, sem `AUTH_USER_MODEL` customizado)

Nenhuma alteração de schema. Mudança de **uso**: o admin recém-criado passa a ser instanciado com `is_active=True` (mantém login bloqueado apenas pela ausência de senha utilizável, não por `is_active=False` — evita conflito com o campo `is_active` que a UI de tenants já usa para "usuário desativado pelo admin", ver `tenants/views.py:259` e `users/user_views.py:83-97`) e `set_unusable_password()` até a ativação via convite.

## Relationships

```
Tenant 1───* UserProfile *───1 User 1───* TenantAdminInvite
                                  │
                                  └── (User.docuparse_profile aponta para UserProfile, related_name existente)
```

## Notes on legacy behavior being removed

- O padrão `tenant_admin_email = f"admin@{slug}"` (`tenants/views.py:75`) deixa de existir para o caminho de criação via API — ver tasks de remoção.
- A leitura de `ADMIN_PASSWORD` em `_provision_tenant` (`tenants/views.py:37-49`) é removida; a senha deixa de ser definida nesse momento.
- `seed_data.py` (linhas ~135-162) mantém a necessidade de um admin utilizável para ambientes locais/dev (não é razoável exigir envio de email real em seed local) — trocado para gerar uma senha aleatória por tenant nesse comando específico, eliminando o compartilhamento entre tenants sem depender do fluxo de convite (ver research.md).
