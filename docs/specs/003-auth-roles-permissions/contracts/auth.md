# API Contract: Authentication

**Prefix**: `/api/auth/`
**Authentication**: Endpoints públicos (login, register). Demais exigem JWT Bearer token.

---

## POST /api/auth/login

Login com email e senha. Retorna par de tokens JWT.

**Request**:
```json
{
  "email": "usuario@exemplo.com",
  "password": "senha123"
}
```

**Response 200**:
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": 1,
    "name": "João Silva",
    "email": "usuario@exemplo.com",
    "role": {
      "id": "uuid",
      "name": "Operador"
    },
    "permissions": ["inbox.view", "documents.validate", "documents.send"]
  }
}
```

**Response 401** — credenciais inválidas:
```json
{ "detail": "Credenciais inválidas." }
```

**Response 403** — conta inativa:
```json
{ "detail": "Conta inativa. Aguarde ativação pelo administrador." }
```

---

## POST /api/auth/logout

Invalida o refresh token no servidor (blacklist).

**Request**:
```json
{ "refresh": "<jwt_refresh_token>" }
```

**Response 204**: sem corpo

**Response 400** — token inválido ou já blacklistado:
```json
{ "detail": "Token inválido ou já expirado." }
```

---

## POST /api/auth/refresh

Obtém novo access token a partir do refresh token.

**Request**:
```json
{ "refresh": "<jwt_refresh_token>" }
```

**Response 200**:
```json
{ "access": "<novo_jwt_access_token>" }
```

**Response 401** — refresh expirado ou blacklistado:
```json
{ "detail": "Token de refresh inválido ou expirado." }
```

---

## POST /api/auth/register

Auto-cadastro de conta. Conta criada como inativa, sem role.

**Request**:
```json
{
  "name": "Maria Souza",
  "email": "maria@exemplo.com",
  "password": "senhaSegura123"
}
```

**Response 201**:
```json
{
  "id": 2,
  "email": "maria@exemplo.com",
  "name": "Maria Souza",
  "is_active": false,
  "message": "Conta criada. Aguarde ativação pelo administrador."
}
```

**Response 400** — email já cadastrado:
```json
{ "detail": "Este e-mail já está em uso." }
```

**Response 400** — dados inválidos:
```json
{
  "email": ["Este campo é obrigatório."],
  "password": ["A senha deve ter ao menos 8 caracteres."]
}
```

---

## GET /api/auth/me

Retorna dados do usuário autenticado. Exige JWT válido.

**Headers**: `Authorization: Bearer <access_token>`

**Response 200**:
```json
{
  "id": 1,
  "name": "João Silva",
  "email": "usuario@exemplo.com",
  "is_active": true,
  "role": {
    "id": "uuid",
    "name": "Operador"
  },
  "permissions": ["inbox.view", "documents.validate", "documents.send"]
}
```

**Response 401** — token ausente ou inválido:
```json
{ "detail": "Autenticação necessária." }
```
