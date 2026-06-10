# Data Model: Authentication, Roles and Permissions

**Feature**: 003-auth-roles-permissions
**Date**: 2026-06-08

---

## Entidades

### `auth.User` (Django built-in — extensão)

Modelo existente do Django. Campos relevantes para esta feature:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | BigAutoField | PK |
| `username` | CharField (unique) | Preenchido com o email no cadastro |
| `email` | EmailField | Identificador de login |
| `password` | CharField | Hash bcrypt |
| `first_name` | CharField | Nome do usuário |
| `last_name` | CharField | Sobrenome (opcional) |
| `is_active` | BooleanField | `True` = pode logar; `False` = conta desativada |
| `is_staff` | BooleanField | Acesso ao Django admin (apenas superusers) |
| `date_joined` | DateTimeField | Data de criação da conta |

**Regras de negócio**:
- Email é único por usuário (enforced via `username` = email + constraint em `email`)
- Conta criada via auto-cadastro (US5) inicia com `is_active=False`
- Conta criada por admin (US3) inicia com `is_active=True`
- O último usuário ativo com role que contém `users.manage` não pode ser desativado

---

### `UserProfile` (existente em `documents` app — modificado)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUIDField (PK) | |
| `user` | OneToOneField(auth.User) | |
| `tenant` | ForeignKey(Tenant) | Tenant ao qual o usuário pertence |
| `role_ref` | ForeignKey(Role, null=True, on_delete=PROTECT) | Role atribuída ao usuário |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

**Mudança em relação ao estado atual**: O campo `role` (CharField com TextChoices OPERATOR/SUPERVISOR/ADMIN) será substituído por `role_ref` (FK para o novo modelo `Role`). O campo antigo será removido após data migration.

**Regras de negócio**:
- Um usuário tem exatamente uma role ativa (ou nenhuma, se conta auto-cadastrada ainda não ativada)
- A role de um usuário pode ser alterada por admins; a mudança reflete no próximo login do usuário

---

### `Permission` (novo, app `users`)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUIDField (PK) | |
| `code` | CharField (unique, max 64) | Código machine-readable, ex: `inbox.view` |
| `description` | CharField (max 255) | Descrição legível, ex: "Visualizar Inbox" |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

**Permissões predefinidas** (criadas via `seed_permissions`):

| Código | Descrição |
|--------|-----------|
| `inbox.view` | Visualizar Inbox |
| `documents.send` | Enviar Documentos |
| `documents.validate` | Validar Documentos |
| `models.create` | Criar Modelos |
| `models.edit` | Editar Modelos |
| `operations.access` | Acessar Operações |
| `users.manage` | Gerenciar Usuários |
| `roles.manage` | Gerenciar Roles |

**Regras de negócio**:
- Permissões são imutáveis por usuários/admins — somente o sistema pode criar/alterar
- O conjunto de permissões é pré-definido e fixo (Assumption do spec)

---

### `Role` (novo, app `users`)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUIDField (PK) | |
| `name` | CharField (unique, max 128) | Nome da role, ex: "Administrador" |
| `permissions` | ManyToManyField(Permission) | Conjunto de permissões |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

**Regras de negócio**:
- Toda role deve ter ao menos uma permissão (validado na API)
- Role com usuários associados não pode ser excluída (verifica `UserProfile.role_ref` antes de deletar)
- Nome deve ser único no sistema

---

## Relacionamentos

```
auth.User (1) ←—— OneToOne ——→ (1) UserProfile
                                       │
                                       │ ForeignKey (role_ref)
                                       ↓
                                     Role
                                       │
                                       │ ManyToMany (permissions)
                                       ↓
                                  Permission
```

---

## Diagrama de estados — Usuário

```
[Auto-cadastro]         [Criado por admin]
      │                       │
      ↓                       ↓
  is_active=False         is_active=True
  role_ref=null           role_ref=<role>
      │                       │
      │ [Admin ativa + atribui role]
      ↓
  is_active=True
  role_ref=<role>
      │
      │ [Admin desativa]    (bloqueado se último admin)
      ↓
  is_active=False
```

---

## Notas de migração

### Migração 0007 — Criar app `users` (Permission, Role)
- Cria tabelas `users_permission` e `users_role`
- Cria tabela M2M `users_role_permissions`

### Migração 0008 — Modificar `UserProfile` (em `documents`)
1. Adicionar `role_ref = ForeignKey(users.Role, null=True, blank=True, on_delete=PROTECT)`
2. **Data migration**: Para cada `UserProfile` com `role` preenchida, buscar ou criar Role correspondente e associar via `role_ref`
3. Remover campo `role` (CharField antigo)
4. Alterar `role_ref` para `null=False` (requer todos os profiles terem role)
   - Nota: profiles de contas auto-cadastradas (US5) podem ter `role_ref=null` temporariamente enquanto aguardam ativação → manter `null=True`
