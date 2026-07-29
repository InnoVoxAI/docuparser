# Implementation Plan: Convite Direto de Usuários por Tenant Admin

**Branch**: `019-generalize-tenant-invite` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/019-generalize-tenant-invite/spec.md`

## Summary

Generalizar o mecanismo de convite por email introduzido na feature 017 (`TenantAdminInvite`) para que o tenant admin possa convidar usuários comuns para seu próprio tenant, sem digitar/compartilhar senha — o convidado define a senha ao ativar o link recebido, e a conta já nasce aprovada com o papel escolhido no convite. O modelo é renomeado `TenantAdminInvite` → `Invite` (nenhum campo novo — o papel já vive em `UserProfile.role_ref`, não no convite) e a lógica de emissão/reenvio/ativação em `tenants/invites.py` é generalizada para aceitar qualquer papel não-plataforma. O endpoint `POST /api/users/` (`users/user_views.py::users_list_create_view`) troca o campo `password` por emissão de convite, e corrige de passagem um bug pré-existente onde o tenant do novo usuário era sempre `Tenant.objects.first()` em vez de `request.tenant` (ver research.md R3). O fluxo de auto-cadastro (`register_view`) e sua aprovação manual (`user_detail_update_view`) permanecem intocados.

## Technical Context

**Language/Version**: Python 3.11+ (Django, backend-core) / TypeScript strict (React 19, frontend)

**Primary Dependencies**: Django + Django REST Framework + `django-tenants` (já em uso); `django.core.mail` (já configurado desde a 017 — `EMAIL_BACKEND`/`DEFAULT_FROM_EMAIL`/`FRONTEND_BASE_URL` em `core/settings.py:259-275`, nenhuma dependência nova); React 19 + TanStack Query + Axios (frontend, módulo `admin` já existente)

**Storage**: PostgreSQL, schema público (`SHARED_APPS`) — a tabela renomeada `Invite` continua no mesmo schema onde já vivem `Tenant`/`Domain`/`UserProfile` (`core/settings.py:20-33`)

**Testing**: pytest (backend-core, via `./run_script.sh`), seguindo o padrão de `tenants/tests/test_invites.py` (017); Vitest + React Testing Library (frontend, se houver testes de componente para `UserFormModal.tsx`)

**Target Platform**: Linux containers (Docker Compose), inalterado

**Project Type**: Web application (backend Django + frontend React) — alterações concentradas em `backend-core` (apps `tenants` + `users`) e `frontend` (módulo `admin`)

**Performance Goals**: Sem requisito específico além do já vigente (200ms p95 para endpoints não-processamento) — envio de email permanece síncrono dentro de `POST /api/users/`, mesma decisão já tomada e validada na 017 (baixo volume, ver Scale/Scope)

**Constraints**: Falha no envio do convite NÃO reverte a criação do usuário/perfil (mesma política de 017 — `INVITE_DELIVERY_FAILED`, 500, com reenvio disponível); token nunca é armazenado em claro; `role_id` de convite de tenant admin é restrito a papéis com `is_platform_role=False`; o reenvio deve mirar um usuário específico, não "o admin do tenant" (ver research.md R2), porque um tenant pode ter vários convites pendentes simultâneos

**Scale/Scope**: Volume baixo (convite de usuário é ação administrativa pontual do tenant admin, não self-service em massa) — mesmo perfil de carga da 017

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality** — PASS. `tenants/invites.py` já é um módulo isolado (criado na 017 justamente para manter `views.py` dentro do limite de 400 linhas); a generalização (renomear funções, parametrizar por role/user_id) não deve crescer o arquivo além do limite — se aproximar, extrair `invites.py` em `invites/service.py` + `invites/email.py` é a divisão natural. Type hints obrigatórios (padrão já seguido no arquivo). Nenhuma vulnerabilidade nova: token continua gerado com `secrets` (CSPRNG) e hasheado antes de persistir; `role_id` é validado no servidor contra `is_platform_role=False`, não confiando em nada vindo do frontend além do ID.
- **II. Testing Standards** — PASS, com ação: o fluxo de convite de usuário é uma extensão do fluxo de autenticação/provisionamento (mesma classificação da 017) e por isso REQUER teste de integração (convite → ativação → login, e resend → invalidação do link antigo). O bug do `Tenant.objects.first()` (research.md R3) exige um teste de regressão explícito (criar usuário como admin de um tenant que não é o primeiro do banco, confirmar que o `UserProfile` vai para o tenant correto) — sem esse teste, o bug poderia reaparecer silenciosamente.
- **III. User Experience Consistency** — PASS. Endpoints seguem o envelope `{ "data", "error", "meta" }` já padronizado (ver `contracts/user-invite-api.md`). Mensagens em português, sem stack trace. `UserFormModal.tsx` troca o campo de senha por um select de role já existente (nenhuma tela nova é necessária — o modal já existe, só muda o campo obrigatório).
- **IV. Performance Requirements** — PASS, mesma decisão e mesma justificativa da 017 (envio síncrono aceitável no volume esperado; isolado numa função só para permitir mover para fila depois sem reescrever lógica de negócio).

Nenhuma violação não justificada. `Complexity Tracking` não se aplica.

## Project Structure

### Documentation (this feature)

```text
docs/specs/019-generalize-tenant-invite/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   └── user-invite-api.md
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
docuparse-project/backend-core/
├── tenants/
│   ├── models.py                 # RenameModel TenantAdminInvite -> Invite (migração);
│   │                               #   related_name admin_invites -> invites
│   ├── migrations/                # + migração de rename (RenameModel/RenameField)
│   ├── invites.py                 # generalizado: create_invite(tenant, name, email, role)
│   │                               #   substitui create_admin_invite (que passa a chamar a
│   │                               #   versão genérica com role=admin); resend_invite(tenant,
│   │                               #   user_id) substitui resend_admin_invite (idem, chama a
│   │                               #   versão genérica com o user_id do admin); activate_invite
│   │                               #   inalterado (já é genérico, ver research.md R6)
│   ├── views.py                   # invite_activate_view inalterado; invite_resend_view (017)
│   │                               #   passa a delegar para resend_invite genérico
│   ├── templates/tenants/emails/  # rename admin_invite_subject/body.txt -> invite_subject/body.txt;
│   │                               #   + variável role_display_name no contexto
│   └── tests/
│       └── test_invites.py        # atualizado (imports de Invite) + testes novos de convite
│                                    #   de usuário comum e de reenvio por user_id
└── users/
    ├── serializers.py             # UserCreateSerializer perde `password`, ganha validação
    │                               #   role_id.is_platform_role=False; deixa de fazer
    │                               #   Tenant.objects.first() (bug, ver research.md R3)
    ├── user_views.py               # users_list_create_view (POST) passa a chamar
    │                               #   tenants.invites.create_invite(request.tenant, ...)
    │                               #   em vez de serializer.save() direto;
    │                               #   + user_invite_resend_view (POST /users/{id}/invites/resend/)
    ├── users_urls.py               # + rota de resend
    └── tests/
        └── test_user_invites.py   # NOVO — cobre POST /api/users/ sem senha, resend por
                                     #   user_id, e regressão do bug de tenant

docuparse-project/frontend/src/modules/admin/
├── components/
│   └── UserFormModal.tsx          # modo 'create' perde o campo de senha
├── hooks/
│   └── useUserMutations.ts        # CreateUserInput perde `password`; + useResendInviteMutation
└── routes/
    └── UsersRoute.tsx             # sem mudança estrutural — mesmo modal, campos diferentes
```

**Structure Decision**: Nenhum projeto/serviço novo. A feature se encaixa inteiramente nos apps `tenants`/`users` já existentes do `backend-core` e no módulo `admin` já existente do `frontend` — é uma generalização de código já escrito na 017, não uma feature isolada com estrutura própria. `tenants/invites.py` permanece o único lugar com lógica de convite (evita a duplicação que motivou a feature); `users/user_views.py` passa a ser o consumidor da API genérica em vez de criar usuários com senha diretamente.

## Complexity Tracking

Nenhuma violação da constituição requer justificativa — ver Constitution Check acima.
