# Guia de Administração: Autenticação, Roles e Permissões

**Feature**: 003-auth-roles-permissions  
**Audiência**: Desenvolvedor / Administrador do sistema

---

## Visão Geral do Fluxo de Conta

```
Usuário cria conta (register)
        ↓
   is_active = false
        ↓
Admin ativa + atribui role
        ↓
   is_active = true
        ↓
Usuário consegue fazer login
```

Contas criadas pelo auto-cadastro chegam **inativas por padrão**. Sem ativação e atribuição de role, o login retorna `403 Forbidden`.

---

## Parte 1: Bootstrap — Primeiro Admin (desenvolvedor)

Antes de qualquer usuário conseguir administrar o sistema via interface, é preciso criar o **primeiro usuário administrador manualmente** pelo terminal.

### 1.1 Pré-requisitos

> **Importante**: O Docker usa PostgreSQL como banco de dados. Rodar `manage.py` localmente (fora do container) conecta a um SQLite separado e **não afeta o banco usado pela aplicação**. Todos os comandos de bootstrap devem ser executados via `docker compose exec`.

```bash
cd docuparse-project

# Garantir que as permissões foram criadas no banco do Docker
docker compose exec backend-core python manage.py seed_permissions
```

### 1.2 Criar o primeiro admin via docker compose exec

```bash
cd docuparse-project

docker compose exec backend-core python manage.py shell -c "
from django.contrib.auth import get_user_model
from users.models import Permission, Role
from documents.models import Tenant, UserProfile

User = get_user_model()

tenant, _ = Tenant.objects.get_or_create(slug='tenant-demo', defaults={'name': 'Demo'})

admin_role, _ = Role.objects.get_or_create(name='Administrador')
admin_role.permissions.set(Permission.objects.all())

admin_email = 'admin@docuparse.com'
admin_password = 'admin123'  # TROQUE ISSO em produção

u, created = User.objects.get_or_create(
    username=admin_email,
    defaults={'email': admin_email, 'first_name': 'Admin', 'is_active': True}
)
if created:
    u.set_password(admin_password)
    u.save()
    UserProfile.objects.create(user=u, tenant=tenant, role_ref=admin_role)
    print('Admin criado:', admin_email)
else:
    print('Usuário já existe:', admin_email)
"
```

Após isso, acesse `http://localhost:5173` e faça login com as credenciais acima.

---

## Parte 2: Gerenciamento via Interface (admin logado)

Com o admin logado, a barra lateral exibe dois itens extras visíveis apenas para quem tem as permissões `users.manage` e `roles.manage`:

- **Gerenciar Usuários**
- **Gerenciar Roles**

### 2.1 Ativar uma conta pendente

1. Abra **Gerenciar Usuários** na barra lateral.
2. Localize o usuário com status **inativo**.
3. Clique em **Ativar** e selecione uma role para o usuário.
4. Confirme. O usuário já pode fazer login imediatamente.

> Se o usuário não tiver uma role atribuída ao ser ativado, o login será bem-sucedido mas todos os endpoints protegidos retornarão `403`, pois não há permissões associadas.

### 2.2 Criar um usuário diretamente

1. Abra **Gerenciar Usuários**.
2. Clique em **Novo Usuário**.
3. Preencha nome, e-mail, senha e selecione a role.
4. Usuários criados pelo admin chegam **ativos** (diferente do auto-cadastro).

### 2.3 Desativar um usuário

1. Abra **Gerenciar Usuários**.
2. Localize o usuário e clique em **Desativar**.
3. O sistema impede a desativação do **último administrador ativo** (retorna erro 409).

### 2.4 Criar e editar roles

1. Abra **Gerenciar Roles**.
2. Clique em **Nova Role**, dê um nome e selecione as permissões.
3. Para editar, clique na role e ajuste as permissões.
4. Roles em uso (com usuários associados) **não podem ser removidas** (retorna 409).

---

## Parte 3: Gerenciamento via API (admin logado)

Útil para automações, scripts ou quando a interface não está disponível.

### 3.1 Obter token de acesso

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@docuparse.com", "password": "admin123"}'
```

Salve o `access` token:

```bash
ADMIN_TOKEN="<access_token_aqui>"
```

### 3.2 Listar usuários pendentes

```bash
curl -X GET http://localhost:8000/api/ocr/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 3.3 Ativar um usuário e atribuir role

```bash
# Primeiro, obtenha o ID da role
curl -X GET http://localhost:8000/api/ocr/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN"

ROLE_ID="<id_da_role>"
USER_ID="<id_do_usuario>"

curl -X PATCH http://localhost:8000/api/ocr/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"is_active\": true, \"role_id\": \"$ROLE_ID\"}"
```

### 3.4 Criar role com permissões específicas

```bash
curl -X POST http://localhost:8000/api/ocr/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Operador",
    "permission_codes": ["inbox.view", "documents.validate", "documents.send"]
  }'
```

---

## Parte 4: Permissões disponíveis

As permissões são criadas pelo comando `seed_permissions` e são imutáveis (não podem ser criadas ou deletadas pela interface):

| Código               | Descrição              | Acesso concedido                      |
|----------------------|------------------------|---------------------------------------|
| `inbox.view`         | Visualizar Inbox       | Listagem de documentos na fila        |
| `documents.send`     | Enviar Documentos      | Upload de documentos                  |
| `documents.validate` | Validar Documentos     | Aprovação e rejeição de documentos    |
| `models.create`      | Criar Modelos          | Criação de modelos de extração        |
| `models.edit`        | Editar Modelos         | Edição de modelos existentes          |
| `operations.access`  | Acessar Operações      | Tela de operações administrativas     |
| `users.manage`       | Gerenciar Usuários     | CRUD de usuários + ativação/desativação |
| `roles.manage`       | Gerenciar Roles        | CRUD de roles + associação de permissões |

> **Atenção**: Um usuário é considerado **administrador** apenas se tiver **ambas** `users.manage` e `roles.manage`. O sistema impede que o último usuário com esse par de permissões seja desativado.

---

## Parte 5: Troubleshooting

### "Conta criada! Aguarde a ativação pelo administrador."
O usuário se auto-cadastrou. Para ativar:
- Via interface: siga a seção 2.1 acima.
- Via API: siga a seção 3.3 acima.
- Via shell: `User.objects.filter(email='...').update()` + `UserProfile...role_ref = ...`.

### Login retorna `403` mesmo com conta ativa
O usuário está ativo mas não tem role atribuída, ou a role não tem permissões. Verifique via `GET /api/ocr/users/<id>` e atribua uma role com `PATCH`.

### "Não é possível desativar o último administrador ativo"
O sistema protege contra lock-out. Crie outro usuário com `users.manage` + `roles.manage` antes de desativar o atual.

### Permissão removida não refletiu imediatamente
As permissões são verificadas em **tempo real** a cada requisição (não ficam no JWT). Se o token for válido mas a role não tiver mais a permissão, o acesso já é bloqueado sem necessidade de re-login.

---

## Referência Rápida de Endpoints

| Método | Endpoint                        | Permissão requerida | Descrição                     |
|--------|---------------------------------|---------------------|-------------------------------|
| POST   | `/api/auth/login`               | —                   | Login (retorna access + refresh) |
| POST   | `/api/auth/logout`              | —                   | Logout (invalida refresh token) |
| POST   | `/api/auth/refresh`             | —                   | Renovar access token          |
| GET    | `/api/auth/me`                  | Autenticado         | Dados do usuário atual        |
| POST   | `/api/auth/register`            | —                   | Auto-cadastro (inativo)       |
| GET    | `/api/ocr/users`                | `users.manage`      | Listar usuários               |
| POST   | `/api/ocr/users`                | `users.manage`      | Criar usuário (ativo)         |
| GET    | `/api/ocr/users/<id>`           | `users.manage`      | Detalhe do usuário            |
| PATCH  | `/api/ocr/users/<id>`           | `users.manage`      | Ativar/desativar, trocar role |
| GET    | `/api/ocr/roles`                | `roles.manage`      | Listar roles                  |
| POST   | `/api/ocr/roles`                | `roles.manage`      | Criar role                    |
| GET    | `/api/ocr/roles/<id>`           | `roles.manage`      | Detalhe da role               |
| PATCH  | `/api/ocr/roles/<id>`           | `roles.manage`      | Editar role                   |
| DELETE | `/api/ocr/roles/<id>`           | `roles.manage`      | Remover role (se não estiver em uso) |
| GET    | `/api/ocr/permissions`          | `roles.manage`      | Listar permissões disponíveis |
