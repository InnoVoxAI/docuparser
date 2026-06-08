# API Contract: User and Role Management

**Prefix**: `/api/ocr/users/`, `/api/ocr/roles/`, `/api/ocr/permissions/`
**Authentication**: JWT Bearer token obrigatório. Endpoints de gestão exigem permissões específicas.

---

## Permissions API

### GET /api/ocr/permissions

Lista todas as permissões disponíveis no sistema.

**Permissão requerida**: qualquer usuário autenticado

**Response 200**:
```json
[
  { "code": "inbox.view",         "description": "Visualizar Inbox" },
  { "code": "documents.send",     "description": "Enviar Documentos" },
  { "code": "documents.validate", "description": "Validar Documentos" },
  { "code": "models.create",      "description": "Criar Modelos" },
  { "code": "models.edit",        "description": "Editar Modelos" },
  { "code": "operations.access",  "description": "Acessar Operações" },
  { "code": "users.manage",       "description": "Gerenciar Usuários" },
  { "code": "roles.manage",       "description": "Gerenciar Roles" }
]
```

---

## Roles API

### GET /api/ocr/roles

Lista todas as roles com suas permissões.

**Permissão requerida**: `roles.manage`

**Response 200**:
```json
[
  {
    "id": "uuid",
    "name": "Operador",
    "permissions": ["inbox.view", "documents.validate", "documents.send"],
    "users_count": 5,
    "created_at": "2026-06-08T00:00:00Z"
  }
]
```

---

### POST /api/ocr/roles

Cria nova role.

**Permissão requerida**: `roles.manage`

**Request**:
```json
{
  "name": "Coordenador",
  "permission_codes": ["inbox.view", "documents.validate", "users.manage"]
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "name": "Coordenador",
  "permissions": ["inbox.view", "documents.validate", "users.manage"],
  "users_count": 0,
  "created_at": "2026-06-08T00:00:00Z"
}
```

**Response 400** — sem permissões:
```json
{ "detail": "Uma role deve ter ao menos uma permissão." }
```

**Response 400** — nome duplicado:
```json
{ "detail": "Já existe uma role com este nome." }
```

**Response 400** — código de permissão inválido:
```json
{ "detail": "Permissão 'xyz' não existe." }
```

---

### GET /api/ocr/roles/:id

Retorna detalhes de uma role.

**Permissão requerida**: `roles.manage`

**Response 200**: mesmo formato do item em GET /api/ocr/roles

**Response 404**: role não encontrada

---

### PATCH /api/ocr/roles/:id

Atualiza nome e/ou permissões de uma role.

**Permissão requerida**: `roles.manage`

**Request** (campos opcionais):
```json
{
  "name": "Coordenador Sênior",
  "permission_codes": ["inbox.view", "documents.validate", "users.manage", "models.create"]
}
```

**Response 200**: role atualizada

**Response 400** — tentativa de remover todas as permissões:
```json
{ "detail": "Uma role deve ter ao menos uma permissão." }
```

---

### DELETE /api/ocr/roles/:id

Remove uma role. Bloqueado se existirem usuários com esta role.

**Permissão requerida**: `roles.manage`

**Response 204**: role removida

**Response 409** — role em uso:
```json
{ "detail": "Esta role está atribuída a 3 usuário(s) e não pode ser removida." }
```

---

## Users API

### GET /api/ocr/users

Lista todos os usuários com suas roles.

**Permissão requerida**: `users.manage`

**Response 200**:
```json
[
  {
    "id": 1,
    "name": "João Silva",
    "email": "joao@exemplo.com",
    "is_active": true,
    "role": {
      "id": "uuid",
      "name": "Operador"
    },
    "date_joined": "2026-06-01T00:00:00Z"
  }
]
```

---

### POST /api/ocr/users

Cria novo usuário (ativo, com role).

**Permissão requerida**: `users.manage`

**Request**:
```json
{
  "name": "Ana Lima",
  "email": "ana@exemplo.com",
  "password": "senhaSegura123",
  "role_id": "uuid"
}
```

**Response 201**:
```json
{
  "id": 3,
  "name": "Ana Lima",
  "email": "ana@exemplo.com",
  "is_active": true,
  "role": { "id": "uuid", "name": "Operador" },
  "date_joined": "2026-06-08T00:00:00Z"
}
```

**Response 400** — email duplicado:
```json
{ "detail": "Este e-mail já está em uso." }
```

**Response 400** — role não encontrada:
```json
{ "detail": "Role não encontrada." }
```

---

### GET /api/ocr/users/:id

Retorna detalhes de um usuário.

**Permissão requerida**: `users.manage`

**Response 200**: mesmo formato do item em GET /api/ocr/users

---

### PATCH /api/ocr/users/:id

Atualiza dados de um usuário.

**Permissão requerida**: `users.manage`

**Request** (campos opcionais):
```json
{
  "name": "João Oliveira",
  "email": "joao.novo@exemplo.com",
  "role_id": "outro-uuid",
  "is_active": false
}
```

**Response 200**: usuário atualizado

**Response 409** — tentativa de desativar o último administrador ativo (usuário com permissão `users.manage` e `roles.manage`):
```json
{ "detail": "Não é possível desativar o último administrador ativo do sistema." }
```

**Nota**: "último administrador" é definido como o último usuário ativo cuja role contém **ambas** as permissões `users.manage` e `roles.manage`.
