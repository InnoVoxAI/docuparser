# Quickstart: Integration Test Scenarios

**Feature**: 003-auth-roles-permissions
**Date**: 2026-06-08

---

## Pré-requisitos

```bash
# Setup inicial (rodar uma vez)
cd docuparse-project/backend-core
python manage.py migrate
python manage.py seed_permissions

# O tenant padrão será criado automaticamente quando necessário
```

---

## Cenário 1: Fluxo completo de login e logout

Valida US1 (P1).

```bash
# 1. Tentar acessar endpoint protegido sem token
curl -X GET http://localhost:8000/api/auth/me
# Esperado: 401 Unauthorized

# 2. Criar usuário admin via Django shell (setup inicial)
python manage.py shell -c "
from django.contrib.auth import get_user_model
from users.models import Permission, Role
User = get_user_model()

# Criar role Admin com todas as permissões
admin_role = Role.objects.create(name='Administrador')
admin_role.permissions.set(Permission.objects.all())

# Criar usuário admin
u = User.objects.create_user(username='admin@docuparse.com', email='admin@docuparse.com', 
    password='admin123', first_name='Admin', is_active=True)
from documents.models import Tenant, UserProfile
tenant, _ = Tenant.objects.get_or_create(slug='tenant-demo', defaults={'name': 'Demo'})
UserProfile.objects.create(user=u, tenant=tenant, role_ref=admin_role)
"

# 3. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@docuparse.com", "password": "admin123"}'
# Esperado: 200 com access + refresh + user.permissions = todos os 8 códigos

# 4. Acessar /me com token
ACCESS_TOKEN="<token_do_passo_3>"
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# Esperado: 200 com dados do usuário e permissions

# 5. Logout
REFRESH_TOKEN="<refresh_do_passo_3>"
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}"
# Esperado: 204

# 6. Tentar usar o refresh blacklistado
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}"
# Esperado: 401
```

---

## Cenário 2: Controle de acesso por role

Valida US2 (P2).

```bash
# Setup: criar role Operador com permissões limitadas
python manage.py shell -c "
from users.models import Permission, Role
from django.contrib.auth import get_user_model
from documents.models import Tenant, UserProfile
User = get_user_model()
tenant = Tenant.objects.get(slug='tenant-demo')

op_role = Role.objects.create(name='Operador')
op_role.permissions.set(Permission.objects.filter(code__in=['inbox.view', 'documents.validate', 'documents.send']))

op_user = User.objects.create_user(username='operador@docuparse.com', email='operador@docuparse.com',
    password='op123', first_name='Operador', is_active=True)
UserProfile.objects.create(user=op_user, tenant=tenant, role_ref=op_role)
"

# Login como operador
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "operador@docuparse.com", "password": "op123"}'
# Esperado: 200, permissions = ['inbox.view', 'documents.validate', 'documents.send']

OP_TOKEN="<access_token_operador>"

# Tentar acessar gestão de usuários com role de Operador
curl -X GET http://localhost:8000/api/ocr/users \
  -H "Authorization: Bearer $OP_TOKEN"
# Esperado: 403 Forbidden

# Acessar inbox (permitido para Operador)
curl -X GET http://localhost:8000/api/ocr/documents \
  -H "Authorization: Bearer $OP_TOKEN"
# Esperado: 200
```

---

## Cenário 3: Gestão de usuários pelo admin

Valida US3 (P3).

```bash
ADMIN_TOKEN="<access_token_admin>"

# Criar novo usuário
curl -X POST http://localhost:8000/api/ocr/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Novo Usuário",
    "email": "novo@docuparse.com",
    "password": "senha123",
    "role_id": "<id_role_operador>"
  }'
# Esperado: 201 com is_active=true

# Desativar usuário
curl -X PATCH http://localhost:8000/api/ocr/users/<id_usuario> \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
# Esperado: 200

# Tentar login com conta desativada
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "novo@docuparse.com", "password": "senha123"}'
# Esperado: 403 com mensagem de conta inativa

# Tentar desativar o único admin ativo
curl -X PATCH http://localhost:8000/api/ocr/users/<id_admin> \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
# Esperado: 409 com mensagem de último administrador
```

---

## Cenário 4: Gestão de roles e permissões

Valida US4 (P4).

```bash
ADMIN_TOKEN="<access_token_admin>"

# Criar nova role
curl -X POST http://localhost:8000/api/ocr/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Coordenador",
    "permission_codes": ["inbox.view", "documents.validate", "users.manage"]
  }'
# Esperado: 201

ROLE_ID="<id_da_role_criada>"

# Editar permissões da role
curl -X PATCH http://localhost:8000/api/ocr/roles/$ROLE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permission_codes": ["inbox.view", "documents.validate"]}'
# Esperado: 200

# Tentar criar role sem permissões
curl -X POST http://localhost:8000/api/ocr/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Vazia", "permission_codes": []}'
# Esperado: 400

# Tentar remover role em uso
curl -X DELETE http://localhost:8000/api/ocr/roles/<id_role_em_uso> \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Esperado: 409

# Remover role sem usuários
curl -X DELETE http://localhost:8000/api/ocr/roles/$ROLE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Esperado: 204
```

---

## Cenário 5: Auto-cadastro e ativação

Valida US5 (P5).

```bash
# Auto-cadastro
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Novo Colaborador",
    "email": "colaborador@empresa.com",
    "password": "senha123"
  }'
# Esperado: 201 com is_active=false

# Tentar login antes da ativação
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "colaborador@empresa.com", "password": "senha123"}'
# Esperado: 403

# Admin ativa e atribui role
ADMIN_TOKEN="<access_token_admin>"
USER_ID="<id_colaborador>"
curl -X PATCH http://localhost:8000/api/ocr/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true, "role_id": "<id_role_operador>"}'
# Esperado: 200

# Login após ativação
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "colaborador@empresa.com", "password": "senha123"}'
# Esperado: 200 com tokens e permissions do Operador
```

---

## Cenário 6: Reflexo imediato de remoção de permissão

Valida SC-003 e FR-017.

```bash
# Remover permissão de uma role enquanto usuário está autenticado
ADMIN_TOKEN="<access_token_admin>"
curl -X PATCH http://localhost:8000/api/ocr/roles/<id_role_operador> \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permission_codes": ["inbox.view"]}'  # remove documents.validate
# Esperado: 200

# Tentar validar documento com token ainda válido do Operador
OP_TOKEN="<access_token_operador_ainda_valido>"
curl -X POST http://localhost:8000/api/ocr/documents/<id>/validate \
  -H "Authorization: Bearer $OP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved"}'
# Esperado: 403 (permissão verificada em tempo real, não no token)
```
