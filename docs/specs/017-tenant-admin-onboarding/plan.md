# Implementation Plan: Onboarding do Administrador de Tenant via Convite por Email

**Branch**: `017-tenant-admin-onboarding` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/017-tenant-admin-onboarding/spec.md`

## Summary

Substituir o padrão atual de provisionamento de tenant — email fake `admin@{slug}` e senha global compartilhada via `ADMIN_PASSWORD` (`tenants/views.py:24-91`) — por um fluxo real: o operador informa nome/email do administrador ao criar o tenant, o sistema cria a conta sem senha utilizável e envia um convite de ativação por email com um token opaco, de uso único e com expiração, armazenado com hash. Um endpoint público (sem autenticação) permite ao convidado definir sua senha e ativar a conta; um endpoint autenticado permite reenviar o convite. Nenhuma infraestrutura de email existe hoje (research.md R1) — será construída usando o backend nativo do Django (`django.core.mail`), configurável por env var (console em dev/test, SMTP em produção). Código legado (email fake e dependência de `ADMIN_PASSWORD` compartilhado) é removido tanto do endpoint da API quanto, de forma adaptada, do comando `seed_data.py`.

## Technical Context

**Language/Version**: Python 3.11+ (Django, backend-core) / TypeScript strict (React 19, frontend)

**Primary Dependencies**: Django + Django REST Framework + `django-tenants` (backend-core, já em uso); `django.core.mail` (novo uso, biblioteca já disponível no framework — nenhuma dependência nova); React 19 + React Hook Form + Zod + TanStack Query + Axios (frontend, convenções de `docuparse-project/frontend/frontend_rules.md`)

**Storage**: PostgreSQL, schema público (`SHARED_APPS`) para a nova tabela `TenantAdminInvite` — mesmo schema onde já vivem `Tenant`/`Domain`/`UserProfile` (`core/settings.py:20-33`)

**Testing**: pytest (backend-core, via `./run_script.sh`) seguindo o padrão de `tenants/tests/test_provisioning.py`; Vitest + React Testing Library (frontend)

**Target Platform**: Linux containers (Docker Compose), consistente com o resto do projeto

**Project Type**: Web application (backend Django + frontend React), alterações concentradas em `backend-core` (app `tenants` + `users`) e `frontend` (módulo `admin`)

**Performance Goals**: Sem requisito de performance específico além do já vigente para `Backend Core non-processing endpoints` na constituição (200ms p95) — envio de email é potencialmente lento/instável e por isso NÃO deve bloquear a resposta de criação do tenant além do necessário (ver Constraints)

**Constraints**: A falha no envio do email de convite NÃO deve reverter a criação do tenant/usuário (ver contrato `INVITE_DELIVERY_FAILED`, 500) — o operador pode reenviar; token de convite nunca é armazenado em claro no banco (apenas seu hash); endpoint de ativação é público e não deve vazar se um email/token existe ou não além do necessário para UX (mensagens genéricas o suficiente, sem enumerar contas)

**Scale/Scope**: Volume de criação de tenants é baixo (operação administrativa esporádica, não self-service em massa) — não há requisito de alta concorrência para este fluxo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality** — PASS. Funções novas (serviço de convite, view de ativação/reenvio) seguem os limites de tamanho já praticados no arquivo (`tenants/views.py` já teria ~400 linhas somando o novo código; será dividido em um módulo `tenants/invites.py` para não violar o limite de 400 linhas por arquivo). Type hints obrigatórios (já é o padrão do arquivo, `from __future__ import annotations` + hints presentes). Nenhuma vulnerabilidade OWASP introduzida — token gerado com `secrets` (CSPRNG), hasheado antes de persistir, validado em fronteira de sistema (endpoint público).
- **II. Testing Standards** — PASS, com ação: **Autenticação** está listada como exigindo teste de integração — o novo fluxo de convite/ativação é, na prática, uma extensão do fluxo de autenticação/provisionamento e por isso REQUER testes de integração (criação de tenant → convite → ativação → login), não apenas testes unitários. Regression test para o comportamento antigo (que deixa de existir) não se aplica — é remoção deliberada, coberta por teste explícito de que o padrão antigo não é mais produzido.
- **III. User Experience Consistency** — PASS. Todos os novos endpoints seguem o envelope `{ "data", "error", "meta" }` já padronizado (ver `contracts/tenant-admin-invite-api.md`). Mensagens de erro em português, sem stack trace, seguindo o padrão de `tenants/views.py`/`users/auth_views.py`. Frontend deve tratar estados de loading/erro no novo formulário e na nova tela de ativação (RHF + Zod, conforme `frontend_rules.md`).
- **IV. Performance Requirements** — PASS, com atenção: o envio de email síncrono dentro de `POST /api/admin/tenants/` pode ultrapassar o orçamento de 200ms p95 se o SMTP externo for lento. Decisão: manter síncrono nesta primeira entrega (volume baixo, ver Scale/Scope) mas isolar a chamada de envio em uma função só, para permitir mover para uma fila assíncrona depois sem reescrever a lógica de negócio — não introduzir infraestrutura de fila agora seria over-engineering para o volume esperado.

Nenhuma violação não justificada. `Complexity Tracking` não se aplica.

## Project Structure

### Documentation (this feature)

```text
docs/specs/017-tenant-admin-onboarding/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   └── tenant-admin-invite-api.md
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
docuparse-project/backend-core/
├── core/
│   └── settings.py             # + EMAIL_BACKEND/EMAIL_HOST_*/DEFAULT_FROM_EMAIL/
│                                #   TENANT_ADMIN_INVITE_TTL_HOURS/FRONTEND_BASE_URL
├── tenants/
│   ├── models.py                # + TenantAdminInvite
│   ├── migrations/               # + migração para TenantAdminInvite
│   ├── serializers.py            # TenantCreateSerializer + admin_name/admin_email
│   ├── invites.py                # NOVO — geração/validação/envio de convite (mantém
│   │                              #   views.py dentro do limite de 400 linhas)
│   ├── views.py                  # _provision_tenant alterado; +invite_activate_view,
│   │                              #   +invite_resend_view; remove geração de email fake
│   ├── urls.py                   # + rotas de invites/activate e invites/resend
│   └── tests/
│       ├── test_provisioning.py  # atualizado (sem mais ADMIN_PASSWORD/email fake)
│       └── test_invites.py       # NOVO
└── users/
    └── management/commands/
        └── seed_data.py          # ajustado: senha aleatória por tenant, sem
                                    #   compartilhar ADMIN_PASSWORD entre tenants

docuparse-project/frontend/src/modules/admin/
├── components/
│   ├── TenantCreateForm.tsx      # + campos admin_name/admin_email
│   └── TenantsTable.tsx          # (eventual indicador de convite pendente/reenviar)
├── services/                     # tenants.service.ts com os novos campos/erros
└── index.ts

docuparse-project/frontend/src/modules/tenant-activation/   # NOVO módulo
├── components/
│   └── ActivateAccountForm.tsx
├── services/
│   └── tenantActivation.service.ts
├── types.ts
└── index.ts                      # rota pública /ativar-conta/:token
```

**Structure Decision**: Web application com backend Django (`backend-core`) e frontend React (`frontend`), ambos já existentes. Nenhum projeto/serviço novo é criado — a feature se encaixa nos apps `tenants`/`users` do backend-core e em um novo módulo de frontend (`tenant-activation`) para a tela pública de ativação, seguindo a convenção de "um módulo por domínio" de `frontend_rules.md`. A lógica de convite fica isolada em `tenants/invites.py` para não estourar o limite de 400 linhas por arquivo já próximo do limite em `tenants/views.py`.

## Complexity Tracking

Nenhuma violação da constituição requer justificativa — ver Constitution Check acima.
