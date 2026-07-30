---
title: '019 - Generalize Tenant Invite: Fase 5/6 (US3 + Polish)'
type: note
permalink: docuparser/features/019-generalize-tenant-invite-fase-5-6-us3-polish
tags:
- feature-019
- tenants
- invites
- users
---

## Status

Fases 5 (US3 — reenvio de convite por `user_id`) e 6 (Polish/FR-016) da feature `019-generalize-tenant-invite` implementadas (T019-T030). Continuação de [[019 - Generalize Tenant Invite: Fase 3/4 (US1 + US2)]]. Todas as 30 tarefas de `tasks.md` estão agora marcadas `[X]` — feature completa.

## O que mudou

- **`user_invite_resend_view`** (novo, `docuparse-project/backend-core/users/user_views.py`): `POST` com `require_permission("users.manage")`. Resolve `UserProfile` por `user_id` **e** `tenant=request.tenant` (404 `USER_NOT_FOUND` se não achar — sem distinguir "não existe" de "existe em outro tenant", por design); chama `tenants.invites.resend_invite(request.tenant, user_id)`; 409 `USER_ALREADY_ACTIVE` se `InviteeAlreadyActiveError`.
- Rota nova em `users_urls.py`: `users/<int:user_id>/invites/resend/`. Prefixo real da app é `/api/ocr/` (`core/urls.py`), **não** `/api/users/` como o `contracts/user-invite-api.md`/`quickstart.md` sugeriam — corrigi o `quickstart.md` para `/api/ocr/users`.
- **`UserListSerializer`** ganhou `invite_pending` (`SerializerMethodField` → `not obj.has_usable_password()`) para o frontend saber quando mostrar "Reenviar convite" sem expor `has_usable_password` diretamente.
- Frontend: `AdminUser.invite_pending?: boolean` (`types.ts`); `useUserMutations.ts` ganhou `resendInvite`/`isResendingInvite`; `UserTable.tsx` mostra botão "Reenviar convite" só quando `u.invite_pending`; `GerenciarUsuarios.tsx` faz o wiring (loading por `resendingUserId`, erro via `alert`).
- **FR-016** (`tenant_users_view` POST, `docuparse-project/backend-core/tenants/views.py`): parava de criar usuário com senha em texto (`User.objects.create_user(..., password=password)`) — agora chama `tenants.invites.create_invite(tenant, name, email, role)`, mesma função usada por `users_list_create_view`. `tenant` continua vindo do `slug` da URL (não sofre do bug FR-015). **Sem** a restrição `is_platform_role=False` — o operador de plataforma pode legitimamente atribuir role admin do tenant.
- `TenantUsersPanel.tsx`: removido o campo de senha do form "Convidar" (rótulo já existia, agora bate com o comportamento real).
- T028 (rename `TenantAdminInvite`→`Invite` em `tenants/tests/`) já estava completo desde a Fase 2 — confirmado por grep, nenhuma mudança necessária.

## Achado durante a validação manual (T029)

Rodei o quickstart ponta a ponta contra o Postgres real do devcontainer (não só pytest) e o banco dev **não tinha a migração `tenants.0006_rename_tenantadmininvite_to_invite` aplicada no schema `public`** — `information_schema.tables` mostrava `tenants_tenantadmininvite` (nome antigo) em `public`, causando `ProgrammingError: relation "tenants_invite" does not exist` em qualquer convite. Resolvido rodando `manage.py migrate_schemas --shared`. Isso é estado do banco de dev, não bug de código — mas é bom lembrar que qualquer ambiente (dev, staging) precisa rodar `migrate_schemas --shared` após esta feature, não só `migrate`. `Tenant.objects.create(...)` sem `auto_create_schema=False` explícito **cria um schema novo de verdade** (`auto_create_schema=True` é o default do django-tenants) — cuidado ao seedar dados de teste manualmente em shell, isso já dispara `migrate_schemas` para o schema novo sozinho.

## Verificação

- `pytest users/ tenants/` via `run_script.sh .venv/bin/python -m pytest`: 86 passed (10 novos em `test_user_invites.py::UserInviteResendTests` + `test_invites.py::TenantUsersInviteTests`).
- Frontend: `tsc --noEmit` limpo; `eslint .` sem erros novos (7 warnings pré-existentes, não relacionados).
- Quickstart manual completo (convidar → capturar email console → ativar → logar → reenviar → ativar novo link → confirmar link antigo invalidado → auto-cadastro ainda funciona) rodado contra `manage.py runserver` + Postgres do devcontainer.

Ver [[../../docs/specs/019-generalize-tenant-invite/tasks.md|tasks.md]] — feature completa, todas as 30 tarefas `[X]`.
