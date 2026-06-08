# Tasks: Authentication, Roles and Permissions

**Input**: Design documents from `docs/specs/003-auth-roles-permissions/`

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Branch**: `003-auth-roles-permissions`

**Prerequisites**: plan.md ✅ | spec.md ✅ | data-model.md ✅ | contracts/ ✅ | research.md ✅ | quickstart.md ✅

**Note on tests**: Integration tests are MANDATORY per constitution (Principle II) for authentication flows and permission enforcement. Test tasks are included in each user story phase and must be written before the corresponding implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in this phase)
- **[Story]**: Which user story this task belongs to (US1–US5)
- All paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `users` Django app skeleton and configure backend settings and URL routing.

- [ ] T001 Create users app directory structure: `docuparse-project/backend-core/users/__init__.py`, `users/apps.py`, `users/migrations/__init__.py`, `users/tests/__init__.py`, `users/management/__init__.py`, `users/management/commands/__init__.py`
- [ ] T002 Add `'users'` and `'rest_framework_simplejwt.token_blacklist'` to `INSTALLED_APPS`; add `SIMPLE_JWT` config (`ACCESS_TOKEN_LIFETIME=timedelta(minutes=15)`, `REFRESH_TOKEN_LIFETIME=timedelta(days=7)`, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`, `AUTH_HEADER_TYPES=('Bearer',)`); add `REST_FRAMEWORK` config with `DEFAULT_AUTHENTICATION_CLASSES = ['rest_framework_simplejwt.authentication.JWTAuthentication']` in `docuparse-project/backend-core/core/settings.py`
- [ ] T003 Add URL routes `path("api/auth/", include("users.auth_urls"))` and `path("api/ocr/", include("users.users_urls"))` to `urlpatterns` in `docuparse-project/backend-core/core/urls.py`

**Checkpoint**: App skeleton created — foundational models and migrations can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, database migrations, and authentication/authorization classes that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Create `Permission` model (fields: `id` UUIDField PK, `code` CharField unique max_length=64, `description` CharField max_length=255, `created_at`, `updated_at`) and `Role` model (fields: `id` UUIDField PK, `name` CharField unique max_length=128, `permissions` ManyToManyField(Permission), `created_at`, `updated_at`) with full Python type hints in `docuparse-project/backend-core/users/models.py`
- [ ] T005 Run `python manage.py makemigrations users` to generate initial migration; verify it creates tables `users_permission`, `users_role`, and `users_role_permissions` in `docuparse-project/backend-core/users/migrations/0001_initial.py`
- [ ] T006 Create idempotent `seed_permissions` management command using `get_or_create` to seed all 8 predefined permissions: `inbox.view` (Visualizar Inbox), `documents.send` (Enviar Documentos), `documents.validate` (Validar Documentos), `models.create` (Criar Modelos), `models.edit` (Editar Modelos), `operations.access` (Acessar Operações), `users.manage` (Gerenciar Usuários), `roles.manage` (Gerenciar Roles) in `docuparse-project/backend-core/users/management/commands/seed_permissions.py`
- [ ] T007 Create migration adding `role_ref = models.ForeignKey('users.Role', null=True, blank=True, on_delete=models.PROTECT, related_name='user_profiles')` to `UserProfile` model in `docuparse-project/backend-core/documents/migrations/0007_userprofile_role_ref.py`
- [ ] T008 Create migration removing the old `role` CharField from `UserProfile` in `docuparse-project/backend-core/documents/migrations/0008_userprofile_remove_role.py`
- [ ] T009 Create `DocuparseAuthentication(JWTAuthentication)` class: attempt JWT auth via `super().authenticate()`; on failure, check if `Authorization` header matches `Bearer <DOCUPARSE_INTERNAL_SERVICE_TOKEN>` and return `(AnonymousUser(), 'service_token')` for inter-service calls; return `None` otherwise in `docuparse-project/backend-core/users/authentication.py`
- [ ] T010 Create `HasDocuparsePermission(BasePermission)` class with `required_permission: str` attribute that checks `request.user.docuparse_profile.role_ref.permissions.filter(code=self.required_permission).exists()`; create `require_permission(code: str) -> type[BasePermission]` factory returning a dynamically-named subclass; return `True` for service token requests (where `request.auth == 'service_token'`) in `docuparse-project/backend-core/users/permissions.py`

**Checkpoint**: Foundation complete — Permission/Role models, migrations, and authentication classes ready.

---

## Phase 3: User Story 1 — Login e Logout (Priority: P1) 🎯 MVP

**Goal**: Authenticated users log in with email/password, receive JWT tokens, access `/api/auth/me`, and revoke access via logout.

**Independent Test**: Create admin user + UserProfile + Role in Django shell → `POST /api/auth/login` returns 200 with access/refresh/permissions → `GET /api/auth/me` returns user data → `POST /api/auth/logout` returns 204 → retry refresh returns 401.

### Tests for User Story 1

> **Write these tests FIRST — ensure they FAIL before implementing T012–T019**

- [ ] T011 [US1] Write integration tests covering: login with valid credentials (200 + access + refresh + user.permissions), login with invalid credentials (401), login with inactive account (403), logout with valid refresh (204), attempt refresh after logout (401), GET /api/auth/me with valid token (200), GET /api/auth/me without token (401) in `docuparse-project/backend-core/users/tests/test_auth_views.py`

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create `LoginSerializer` (fields: `email` EmailField, `password` CharField write-only; `validate()` calls `authenticate(username=email, password=password)`, raises 401 on failure, raises 403 if user is inactive) and `UserMeSerializer` (fields: `id`, `name` from first_name, `email`, `is_active`, `role` as {id, name}, `permissions` as list of codes from role_ref) in `docuparse-project/backend-core/users/serializers.py`
- [ ] T013 [US1] Implement `login_view` (POST /api/auth/login): use `LoginSerializer` to authenticate; generate `RefreshToken.for_user(user)`; return `{"access": str(refresh.access_token), "refresh": str(refresh), "user": UserMeSerializer(user).data}` in `docuparse-project/backend-core/users/auth_views.py`
- [ ] T014 [US1] Implement `logout_view` (POST /api/auth/logout): validate `refresh` field from request body; find `OutstandingToken` and create `BlacklistedToken`; return 204; return 400 with `{"detail": "Token inválido ou já expirado."}` on error in `docuparse-project/backend-core/users/auth_views.py`
- [ ] T015 [US1] Implement `refresh_view` (POST /api/auth/refresh) using `TokenRefreshView` from SimpleJWT; implement `me_view` (GET /api/auth/me) requiring JWT authentication and returning `UserMeSerializer(request.user).data` in `docuparse-project/backend-core/users/auth_views.py`
- [ ] T016 [US1] Create URL patterns: `login/` → `login_view`, `logout/` → `logout_view`, `refresh/` → `refresh_view`, `me/` → `me_view` in `docuparse-project/backend-core/users/auth_urls.py`
- [ ] T017 [P] [US1] Add `AuthContext`, `AuthProvider` (state: `user`, `loading`; methods: `login(email, password)` → POST /api/auth/login → setUser + localStorage; `logout()` → POST /api/auth/logout → clearUser; `hasPermission(code)` → checks `user.permissions.includes(code)`; axios interceptor adding `Authorization: Bearer <token>` to all requests; on mount restore user from localStorage via GET /api/auth/me), and `useAuth()` hook in `docuparse-project/frontend/src/main.jsx`
- [ ] T018 [US1] Add `LoginPage` component with email input, password input, submit button, loading spinner, and error message display; calls `useAuth().login(email, password)` on submit in `docuparse-project/frontend/src/main.jsx`
- [ ] T019 [US1] Wrap `App` root with `<AuthProvider>`; in the root render function, show `<LoginPage>` when `user === null && !loading`, show loading spinner when `loading === true`, and show the main app otherwise in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: US1 complete — users can log in, receive tokens, access /api/auth/me, and logout revokes the session.

---

## Phase 4: User Story 2 — Controle de Acesso por Role (Priority: P2)

**Goal**: Backend enforces permission checks on document endpoints; frontend hides nav items and screens unauthorized to the current user.

**Independent Test**: Log in as Operador (permissions: inbox.view, documents.validate) → GET /api/ocr/users returns 403 → GET /api/ocr/documents returns 200 → Admin removes `documents.validate` from Operador role → Operador's valid JWT POST to validate endpoint returns 403 (real-time enforcement).

### Tests for User Story 2

- [ ] T020 [US2] Write integration tests: authenticated operator blocked on GET /api/ocr/users (403), authenticated admin allowed (200); operator allowed to POST validate; admin removes validate permission from operator role; operator's valid token returns 403 on validate; unauthenticated request returns 401 on all protected endpoints in `docuparse-project/backend-core/users/tests/test_permissions.py`

### Implementation for User Story 2

- [ ] T021 [US2] On `document_validation_view`: add `authentication_classes = [DocuparseAuthentication]` and `permission_classes = [require_permission('documents.validate')]`; remove the `_internal_token_error(request)` guard and its early-return from this specific view in `docuparse-project/backend-core/documents/views.py`
- [ ] T022 [US2] On document list/get endpoints (any view frontend users call): add `authentication_classes = [DocuparseAuthentication]` and `permission_classes = [require_permission('inbox.view')]`; keep `_internal_token_error` on strictly inter-service endpoints (OCR callbacks, upload ingestion) that have no frontend callers in `docuparse-project/backend-core/documents/views.py`
- [ ] T023 [P] [US2] Add `PermissionGuard({ code, children, fallback = null })` component that calls `useAuth().hasPermission(code)` and renders `children` if true or `fallback` if false in `docuparse-project/frontend/src/main.jsx`
- [ ] T024 [US2] Update each item in `NAV_ITEMS` (or equivalent nav configuration) to include a `permission` field; wrap each nav item in `<PermissionGuard code={item.permission}>` so unauthorized items are invisible in the sidebar/menu in `docuparse-project/frontend/src/main.jsx`
- [ ] T025 [US2] Wrap each top-level screen component (Inbox, Validação, Aprovados, Rejeitados, and any future admin screens) with `<PermissionGuard code="..." fallback={<AcessoNaoAutorizado />}>` in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: US2 complete — permission enforcement active on backend (real-time DB query) and frontend (hidden UI); unauthorized access returns 403 or blank screen.

---

## Phase 5: User Story 3 — Gestão de Usuários (Priority: P3)

**Goal**: Admins can create, edit, activate/deactivate users, and change roles via REST API and a management UI screen.

**Independent Test**: Admin POST /api/ocr/users creates user with role (201) → new user logs in → admin PATCH /api/ocr/users/:id with is_active=false (200) → user login returns 403 → admin tries to deactivate themselves as sole admin → 409 → admin reactivates user → login works.

### Tests for User Story 3

- [ ] T026 [US3] Write integration tests: list users (200 with pagination), create user (201 with is_active=true + role), create user with duplicate email (400), get user detail (200), update user role, deactivate user (200), deactivate last admin (409), reactivate user, non-admin accessing /api/ocr/users (403) in `docuparse-project/backend-core/users/tests/test_user_management.py`

### Implementation for User Story 3

- [ ] T027 [P] [US3] Create `UserListSerializer` (id, name, email, is_active, role {id, name}, date_joined), `UserCreateSerializer` (name, email, password write-only min 8 chars, role_id; creates auth.User with username=email + UserProfile with role_ref), `UserUpdateSerializer` (name optional, email optional, role_id optional, is_active optional) in `docuparse-project/backend-core/users/serializers.py`
- [ ] T028 [US3] Implement `users_list_create_view` (GET returns `UserListSerializer(many=True)` filtered by tenant; POST validates `UserCreateSerializer`, creates `User` + `UserProfile`, returns 201); apply `require_permission('users.manage')` in `docuparse-project/backend-core/users/user_views.py`
- [ ] T029 [US3] Implement `user_detail_update_view` (GET returns user detail; PATCH validates `UserUpdateSerializer`; if `is_active=False` call `last_admin_guard` first, return 409 with `{"detail": "Não é possível desativar o último administrador ativo do sistema."}` if blocked); apply `require_permission('users.manage')` in `docuparse-project/backend-core/users/user_views.py`
- [ ] T030 [US3] Implement `last_admin_guard(user_id: int) -> bool` function: queries `UserProfile.objects.filter(user__is_active=True, role_ref__permissions__code__in=['users.manage', 'roles.manage']).exclude(user_id=user_id)` annotated to find users who have BOTH permissions; returns `True` (guard triggered) if count is zero in `docuparse-project/backend-core/users/user_views.py`
- [ ] T031 [US3] Add URL patterns for `users/` (list/create, `users_list_create_view`) and `users/<int:user_id>/` (detail/update, `user_detail_update_view`) in `docuparse-project/backend-core/users/users_urls.py`
- [ ] T032 [US3] Add `GerenciarUsuarios` screen to frontend with: users table (name, email, status badge, role name, actions), "Novo Usuário" button opening a modal with name/email/password/role fields, edit button opening modal to change name/email/role, activate/deactivate toggle; all API calls use axios (JWT interceptor active); requires `users.manage` permission via `PermissionGuard` in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: US3 complete — full user management via API and UI; last-admin protection active; newly created users can log in immediately.

---

## Phase 6: User Story 4 — Gestão de Roles e Permissões (Priority: P4)

**Goal**: Admins can create, edit, and delete roles with permission assignments; constraints prevent empty-permission roles and deletion of in-use roles.

**Independent Test**: POST /api/ocr/roles creates role (201) → assign to user → PATCH role updating permissions → old permission no longer works for user on next request → DELETE role in use returns 409 → DELETE unused role returns 204 → POST role with empty permission_codes returns 400.

### Tests for User Story 4

- [ ] T033 [US4] Write integration tests: list roles (200), list permissions (200), create role with valid permissions (201), create role with empty permission_codes (400), create role with invalid permission code (400), create duplicate role name (400), update role permissions (200), delete unused role (204), delete role in use (409), non-admin accessing roles endpoint (403) in `docuparse-project/backend-core/users/tests/test_role_management.py`

### Implementation for User Story 4

- [ ] T034 [P] [US4] Create `RoleListSerializer` (id, name, permissions as list of codes, users_count annotated field, created_at), `RoleCreateSerializer` (name, permission_codes: validates len ≥ 1 and each code exists in Permission table), `RoleUpdateSerializer` (name optional, permission_codes optional with same validation) in `docuparse-project/backend-core/users/serializers.py`
- [ ] T035 [P] [US4] Implement `permissions_list_view` (GET /api/ocr/permissions): returns `[{"code": p.code, "description": p.description} for p in Permission.objects.all().order_by('code')]`; requires any authenticated user (IsAuthenticated); no admin permission required in `docuparse-project/backend-core/users/permission_views.py`
- [ ] T036 [US4] Implement `roles_list_create_view` (GET returns `RoleListSerializer(many=True)` with `users_count` annotation; POST validates `RoleCreateSerializer`, creates Role + sets permissions, returns 201); apply `require_permission('roles.manage')` in `docuparse-project/backend-core/users/role_views.py`
- [ ] T037 [US4] Implement `role_detail_update_delete_view` (GET returns role detail; PATCH validates `RoleUpdateSerializer`; DELETE checks `UserProfile.objects.filter(role_ref=role).exists()`, returns 409 with `{"detail": "Esta role está atribuída a N usuário(s) e não pode ser removida."}` if in use, else 204); apply `require_permission('roles.manage')` in `docuparse-project/backend-core/users/role_views.py`
- [ ] T038 [US4] Add URL patterns for `permissions/` (`permissions_list_view`), `roles/` (`roles_list_create_view`), and `roles/<uuid:role_id>/` (`role_detail_update_delete_view`) in `docuparse-project/backend-core/users/users_urls.py`
- [ ] T039 [US4] Add `GerenciarRoles` screen with: roles table (name, permissions list, user count, actions), "Nova Role" button opening a modal with name + multi-select permission checkboxes loaded from GET /api/ocr/permissions, edit button opening same modal pre-filled, delete button with confirmation dialog (blocked with toast if role is in use); requires `roles.manage` permission via `PermissionGuard` in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: US4 complete — full role/permission management via API and UI; all business rule constraints enforced.

---

## Phase 7: User Story 5 — Criação de Conta (Priority: P5)

**Goal**: New users self-register and receive an inactive account; admin activates and assigns role; user then logs in normally.

**Independent Test**: POST /api/auth/register → 201 with is_active=false → POST /api/auth/login returns 403 → admin PATCH /api/ocr/users/:id with is_active=true + role_id → POST /api/auth/login returns 200 with tokens.

### Implementation for User Story 5

- [ ] T040 [P] [US5] Create `RegisterSerializer` (fields: name CharField, email EmailField validates uniqueness against `User.objects.filter(email=email)`, password CharField min_length=8 write-only) in `docuparse-project/backend-core/users/serializers.py`
- [ ] T041 [US5] Implement `register_view` (POST /api/auth/register): validate `RegisterSerializer`; create `User` with `username=email`, `is_active=False`; create `UserProfile` with `role_ref=None`; return 201 with `{"id": user.id, "email": user.email, "name": user.first_name, "is_active": False, "message": "Conta criada. Aguarde ativação pelo administrador."}` in `docuparse-project/backend-core/users/auth_views.py`
- [ ] T042 [US5] Add "Criar conta" toggle link below login form on `LoginPage`; when toggled, show registration form (name, email, password, confirm password fields); on submit call POST /api/auth/register; on 201 show success message "Conta criada! Aguarde a ativação pelo administrador." and return to login form in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: US5 complete — self-registration active; accounts start inactive; admin activation flow works end-to-end.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Unit tests, coverage validation, full integration verification, and manual QA.

- [ ] T043 [P] Add unit tests: `seed_permissions` idempotency (call twice → no duplicates, count stays at 8), `last_admin_guard` returns True when target is sole admin and False when another admin exists, `LoginSerializer.validate()` raises 403 for inactive user, `RegisterSerializer` raises 400 for duplicate email in `docuparse-project/backend-core/users/tests/test_permissions.py`
- [ ] T044 Run `python manage.py test users --verbosity=2` and verify all tests pass; run `coverage run manage.py test users && coverage report` and verify ≥ 80% line coverage on users app; fix any failures in `docuparse-project/backend-core/`
- [ ] T045 Run `python manage.py migrate && python manage.py seed_permissions` to verify full migration chain (0001 through 0008); create admin user + Role via Django shell per quickstart.md Cenário 1; verify POST /api/auth/login returns 200 with all 8 permission codes in `docuparse-project/backend-core/`
- [ ] T046 QA manual validation: execute all 6 curl scenarios from `docs/specs/003-auth-roles-permissions/quickstart.md` (login/logout, role-based access, user management, role management, self-registration, real-time permission removal); document each HTTP response against expected; fix any discrepancy

**Checkpoint**: All 5 user stories validated by integration tests, ≥ 80% coverage, migration chain verified, and all QA scenarios confirmed.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Foundational) — BLOCKS all user stories
        ├── Phase 3 (US1 Login) — MVP
        │     └── Phase 4 (US2 Access Control) — needs JWT working
        │           └── Phase 8 (Polish) — depends on all stories
        ├── Phase 5 (US3 Users) — independent after Foundational
        │     └── Phase 8 (Polish)
        ├── Phase 6 (US4 Roles) — independent after Foundational
        │     └── Phase 8 (Polish)
        └── Phase 7 (US5 Register) — needs Phase 3 (auth_views.py exists)
              └── Phase 8 (Polish)
```

### User Story Dependencies

| Story | Depends On | Notes |
|-------|-----------|-------|
| US1 (P1) | Phase 2 Foundational | MVP — implement first |
| US2 (P2) | Phase 2 + US1 | JWT must be working to test permission enforcement |
| US3 (P3) | Phase 2 Foundational | Independent of US1/US2 at backend level |
| US4 (P4) | Phase 2 Foundational | Shares users_urls.py with US3 — coordinate T031 and T038 |
| US5 (P5) | Phase 3 US1 | register endpoint added to existing auth_views.py |

### Within Each User Story

1. Integration tests written FIRST (TDD); verify they FAIL before implementing
2. Serializers before views (views import serializers)
3. Views before URL patterns (urls.py imports view names)
4. Backend complete before frontend API calls are wired

---

## Parallel Opportunities

### Phase 3 (US1): Backend + Frontend in parallel

```bash
# These can start simultaneously:
Task T011: "Write auth integration tests in test_auth_views.py"
Task T012: "Create LoginSerializer + UserMeSerializer in serializers.py"
Task T017: "Add AuthContext + AuthProvider in main.jsx"

# T013-T016 are sequential in auth_views.py (depends on T012)
# T018-T019 are sequential in main.jsx (depends on T017)
```

### Phase 5 + Phase 6 (US3 + US4): Can run in parallel after Phase 2

```bash
# Developer A — US3:
T026 → T027 → T028 → T029 → T030 → T031 → T032

# Developer B — US4:
T033 → T034 → T035 → T036 → T037 → T038 → T039
# NOTE: T027 (US3) and T034 (US4) both write to serializers.py — coordinate or run sequentially
```

### Phase 4 (US2): Backend + PermissionGuard in parallel

```bash
# Backend tasks (views.py):
T020 → T021 → T022

# Frontend PermissionGuard (main.jsx, different file):
T023  # can start while backend is being implemented

# T024, T025 depend on T023 (same file, sequential)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T010) ← CRITICAL BLOCKER
3. Complete Phase 3: US1 Login/Logout (T011–T019)
4. **STOP and VALIDATE**: `python manage.py test users.tests.test_auth_views`
5. Verify LoginPage works in browser, logout revokes access

### Incremental Delivery

1. **Foundation** (Phase 1+2) → Environment ready
2. **US1** (Phase 3) → Users can authenticate → **Deploy/Demo MVP**
3. **US2** (Phase 4) → Permissions enforced on backend + frontend
4. **US3** (Phase 5) → Admin can manage users
5. **US4** (Phase 6) → Admin can manage roles
6. **US5** (Phase 7) → Self-registration available
7. **Polish** (Phase 8) → Tests, coverage, QA validated

### Notes

- **serializers.py grows across phases**: T012 (US1) creates the file; T027 (US3) and T034/T040 (US4/US5) add to it — read the file before each addition to avoid overwrites
- **auth_views.py grows across phases**: T013–T015 (US1) create it; T041 (US5) adds register view — same file, coordinate additions
- **users_urls.py shared by US3 and US4**: T031 creates auth/users routes; T038 adds roles/permissions routes — write T031 with placeholder for T038 or do both in sequence
- **Type hints required** on all Python (constitution I): `def login_view(request: HttpRequest) -> JsonResponse`
- **Error messages in Portuguese**, actionable, no stack traces (constitution III)
- **After deploy**: always run `python manage.py migrate && python manage.py seed_permissions`
