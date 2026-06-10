# Implementation Plan: Authentication, Roles and Permissions

**Branch**: `003-auth-roles-permissions` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/003-auth-roles-permissions/spec.md`

---

## Summary

Implementar sistema de autenticação e autorização baseado em roles para o DocuParse. O backend-core (Django 5 + DRF) receberá um novo app `users` com modelos `Permission` e `Role`, endpoints JWT via SimpleJWT (já instalado), e gestão CRUD de usuários e roles. O frontend React terá tela de login, contexto de autenticação global, guards por permissão nas rotas e menu, e substituição do token estático compartilhado por JWT Bearer tokens para chamadas do usuário.

---

## Technical Context

**Language/Version**: Python 3.10 (backend-core), JavaScript ES2022 (frontend React)

**Primary Dependencies**:
- Backend: Django 5.0.1, djangorestframework 3.14.0, djangorestframework-simplejwt 5.3.1 (já instalado), rest_framework_simplejwt.token_blacklist (novo app)
- Frontend: React 18, Vite 5, axios, lucide-react, tailwindcss

**Storage**: SQLite (dev) / PostgreSQL 16 (produção via Docker)

**Testing**: pytest / Django TestCase, APIClient (DRF)

**Target Platform**: Linux server (Docker Compose), dev local Linux

**Project Type**: Web service (Django DRF backend + React SPA)

**Performance Goals**: auth endpoints ≤ 200ms p95 (SC-001, SC-006)

**Constraints**:
- Não quebrar autenticação inter-serviços existente (token estático `DOCUPARSE_INTERNAL_SERVICE_TOKEN`)
- Sem `AUTH_USER_MODEL` customizado — usar `django.contrib.auth.User` com email como login
- Sem dependências novas de frontend além das já instaladas
- Sem recuperação de senha (fora do escopo — Assumption do spec)

**Scale/Scope**: ~10 usuários simultâneos no MVP; CRUD de roles e usuários de baixo volume

---

## Constitution Check

### I. Code Quality
- ✅ Type hints obrigatórios em todo código Python novo (`users/models.py`, `users/views.py`, etc.)
- ✅ Funções com responsabilidade única; `users/views.py` separado de `documents/views.py`
- ✅ Sem código morto — campo `UserProfile.role` removido após migration
- ✅ Ruff/flake8 deve passar com zero violações no novo app `users`
- ✅ Input de usuário validado nos serializers (email, password, permission_codes)
- ⚠️ **Desvio conhecido**: Os endpoints existentes não seguem o envelope `{data, error, meta}` definido na Constituição (Princípio III). Esta feature adiciona novos endpoints seguindo o mesmo padrão dos existentes (resposta JSON direta) para consistência interna. Uma refatoração global do envelope está fora do escopo.

### II. Testing Standards
- ✅ Integration tests OBRIGATÓRIOS para: login, logout, refresh, register, permission enforcement
- ✅ Unit tests OBRIGATÓRIOS para: serializers, permission check functions, last-admin guard
- ✅ Coverage mínimo ≥ 80% no novo app `users`
- ✅ Regression: cada regra de negócio (FR-010, FR-014, FR-015) com teste dedicado

### III. User Experience Consistency
- ✅ Mensagens de erro em português, acionáveis, sem stack traces
- ✅ Estados loading/success/error na tela de login e nas telas de gestão
- ✅ Bloqueio de acesso não autorizado com feedback visual (não silencioso)

### IV. Performance Requirements
- ✅ Login via JWT é inherentemente rápido (< 200ms p95)
- ✅ Verificação de permissão em tempo real: `UserProfile.role_ref.permissions` — query no DB a cada request protegida (aceitável no volume esperado)

---

## Project Structure

### Documentation (this feature)

```text
docs/specs/003-auth-roles-permissions/
├── plan.md              # Este arquivo
├── spec.md              # Especificação funcional
├── research.md          # Decisões técnicas
├── data-model.md        # Entidades e relacionamentos
├── quickstart.md        # Cenários de teste de integração
├── contracts/
│   ├── auth.md          # Contratos endpoints /api/auth/
│   └── users.md         # Contratos endpoints /api/ocr/users, roles, permissions
└── tasks.md             # Gerado por /speckit-tasks (não criado por este plano)
```

### Source Code (repository root)

```text
docuparse-project/
├── backend-core/
│   ├── core/
│   │   ├── settings.py          # Adicionar: users app, token_blacklist, JWT settings, REST_FRAMEWORK
│   │   └── urls.py              # Adicionar: path("api/auth/", include("users.auth_urls"))
│   ├── documents/
│   │   ├── models.py            # Modificar: UserProfile.role → role_ref FK(Role)
│   │   ├── migrations/
│   │   │   └── 0007_userprofile_role_ref.py  # Nova migration
│   │   └── views.py             # Modificar: adicionar JWT auth check nos endpoints de frontend
│   └── users/                   # NOVO APP
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py            # Permission, Role
│       ├── serializers.py       # Auth, User, Role serializers
│       ├── permissions.py       # Classes DRF: HasPermission, IsAdminUser
│       ├── auth_views.py        # login, logout, refresh, register, me
│       ├── user_views.py        # CRUD usuários
│       ├── role_views.py        # CRUD roles
│       ├── permission_views.py  # Listagem de permissões
│       ├── auth_urls.py         # URLs para /api/auth/
│       ├── users_urls.py        # URLs para /api/ocr/users, roles, permissions
│       ├── management/
│       │   └── commands/
│       │       └── seed_permissions.py
│       ├── migrations/
│       │   └── 0001_initial.py  # Permission, Role
│       └── tests/
│           ├── test_auth_views.py
│           ├── test_user_management.py
│           ├── test_role_management.py
│           └── test_permissions.py
└── frontend/
    └── src/
        └── main.jsx             # Adicionar: AuthContext, LoginPage, permission guards
```

**Structure Decision**: Web application (backend Django + frontend React SPA). Novo app `users` para separação de responsabilidades. Frontend permanece em `main.jsx` (monolito existente) com adição de contexto de autenticação inline.

---

## Phase 0: Research

Decisões técnicas documentadas em [research.md](research.md). Principais decisões:

1. **JWT via SimpleJWT** — já instalado em `requirements.txt`
2. **Token blacklist** — `rest_framework_simplejwt.token_blacklist` para logout
3. **Permission customizada** — não usa `django.contrib.auth.Permission` (ContentType-based)
4. **Login por email** — customização do `TokenObtainPairSerializer`
5. **Novo app `users`** — separação de responsabilidades
6. **Migração `UserProfile.role`** — CharField → ForeignKey(Role)
7. **Auth dual** — JWT para frontend + token estático para inter-serviços (ambos aceitos)
8. **Frontend: Context API + localStorage** — sem novas dependências
9. **seed_permissions** — management command para permissões predefinidas

---

## Phase 1: Design & Contracts

### Configurações de backend (`settings.py`)

Adicionar ao `INSTALLED_APPS`:
```python
'users',
'rest_framework_simplejwt.token_blacklist',
```

Adicionar configuração JWT:
```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

Adicionar configuração DRF (sem quebrar endpoints existentes — não define DEFAULT_PERMISSION_CLASSES globalmente):
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    # Sem DEFAULT_PERMISSION_CLASSES — cada view define suas permissões
}
```

### URLs (`core/urls.py`)

```python
urlpatterns = [
    path("api/auth/",  include("users.auth_urls")),
    path("api/ocr/",   include("documents.urls")),
    path("api/ocr/",   include("users.users_urls")),
]
```

### Modelos (`users/models.py`)

```python
class Permission(TimeStampedModel):
    id = UUIDField(primary_key=True, ...)
    code = CharField(max_length=64, unique=True)
    description = CharField(max_length=255)

class Role(TimeStampedModel):
    id = UUIDField(primary_key=True, ...)
    name = CharField(max_length=128, unique=True)
    permissions = ManyToManyField(Permission, related_name='roles')
```

### Migração `UserProfile` (`documents/migrations/0007_...py`)

```
Step 1: AddField role_ref = FK(Role, null=True, blank=True)
Step 2: Data migration — criar roles legadas e associar profiles existentes
Step 3: Manter role_ref como null=True (contas auto-cadastradas sem role)
Step 4: RemoveField role (CharField antigo)
```

### Classes de permissão DRF (`users/permissions.py`)

```python
class HasDocuparsePermission(BasePermission):
    """Verifica se o usuário JWT tem a permissão requerida via UserProfile.role_ref."""
    required_permission: str  # definido na subclasse ou via kwargs
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'docuparse_profile', None)
        if not profile or not profile.role_ref:
            return False
        return profile.role_ref.permissions.filter(code=self.required_permission).exists()

def require_permission(code: str):
    """Factory que retorna uma classe DRF permission para o código dado."""
    ...
```

### Autenticação dual (`users/authentication.py`)

```python
class DocuparseAuthentication(JWTAuthentication):
    """Tenta JWT, aceita também o token estático interno (para inter-serviços)."""
    ...
```

Endpoints de documentos existentes: substituir `_internal_token_error` por `DocuparseAuthentication` + `HasDocuparsePermission` ou `AllowServiceToken`.

### Frontend — AuthContext (`main.jsx`)

```javascript
const AuthContext = createContext(null)

function AuthProvider({ children }) {
    const [user, setUser] = useState(null)      // {id, name, email, role, permissions}
    const [loading, setLoading] = useState(true)
    
    // Interceptors axios para JWT
    // useEffect para verificar token existente no mount
    // login(email, password) → POST /api/auth/login → setUser
    // logout() → POST /api/auth/logout → limpar localStorage
    // hasPermission(code) → user.permissions.includes(code)
}
```

### Frontend — LoginPage (`main.jsx`)

```javascript
function LoginPage({ onLogin }) {
    // Formulário email + senha
    // Chamada POST /api/auth/login
    // Estados: loading, error
    // onLogin(userData) após sucesso
}
```

### Frontend — Permission Guards

```javascript
function PermissionGuard({ code, children, fallback = null }) {
    const { hasPermission } = useAuth()
    return hasPermission(code) ? children : fallback
}
```

Cada `NAV_ITEMS` e cada tela terá sua permissão associada. Nav items invisíveis para usuários sem permissão.

---

## Dependências entre etapas

```
[1] Novo app users + Permission + Role models
    → [2] seed_permissions
    → [3] Migração UserProfile.role_ref
        → [4] Auth views (login, logout, register, me)
            → [5] User management views (CRUD)
            → [5] Role management views (CRUD)
                → [6] Permission guards nos endpoints existentes
                    → [7] Frontend AuthContext + LoginPage
                        → [8] Frontend permission guards por tela/nav
```

---

## Estratégia de testes

### Backend (pytest / Django TestCase)

**Integration tests** (obrigatórios pela Constituição):
- `test_auth_views.py`: login sucesso, credenciais inválidas, conta inativa, logout, refresh, register, email duplicado
- `test_user_management.py`: CRUD usuários, desativar último admin (deve falhar), alterar role
- `test_role_management.py`: CRUD roles, deletar role em uso (deve falhar), remover todas as permissões (deve falhar)
- `test_permissions.py`: verificação de permissão em tempo real; operador não acessa gestão de usuários

**Unit tests**:
- Serializer validation (email format, password min length)
- `last_admin_guard` — função que verifica se é o último admin
- `seed_permissions` — idempotente, não duplica registros

### Frontend (manual — sem test runner configurado)
- Login com credenciais inválidas → mensagem de erro visível
- Login bem-sucedido → redirect para inbox
- Nav items invisíveis para roles sem permissão
- Logout → redirect para login
- Token expirado → redirect automático para login

---

## Complexidade Tracking

| Decisão | Por que necessária | Alternativa rejeitada |
|---------|-------------------|-----------------------|
| Auth dual (JWT + token estático) | Não quebrar inter-serviços existentes | Migrar todos os endpoints para JWT — quebraria backend-com e workers fora do escopo |
| Custom Permission model | Permissões de funcionalidade/tela, não de CRUD de modelo | django.contrib.auth.Permission — ContentType-based, inadequado para este caso |
| Email como username | Evitar AUTH_USER_MODEL customizado em projeto com migrations existentes | Custom User model — exigiria reset do banco ou migração complexa |
