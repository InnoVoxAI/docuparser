---
title: '019 - Generalize Tenant Invite: Fase 3/4 (US1 + US2)'
type: note
permalink: docuparser/features/019-generalize-tenant-invite-fase-3-4-us1-us2
tags:
- feature-019
- tenants
- invites
- users
---

## Status

Fases 3 (US1 — tenant admin convida usuário) e 4 (US2 — usuário ativa conta) da feature `019-generalize-tenant-invite` implementadas (T008-T018). Continuação de [[019 - Generalize Tenant Invite: Fase 1/2 (Setup + Foundational)]]. Fase 5 (US3 — reenvio por `user_id`) e Fase 6 (Polish, FR-016 no `tenant_users_view`) ainda **não** implementadas.

## O que mudou

- `UserCreateSerializer` (`docuparse-project/backend-core/users/serializers.py`): perdeu o campo `password`; `validate_role_id` agora rejeita roles com `is_platform_role=True` (mensagem "Esta role não pode ser atribuída por convite de tenant admin."); perdeu `create()` — a criação virou responsabilidade da view, porque agora depende de `request.tenant`.
- `users_list_create_view` POST (`docuparse-project/backend-core/users/user_views.py`): **corrige o bug FR-015** — passou a usar `request.tenant` explicitamente (antes usava `Tenant.objects.first()` hardcoded via `UserCreateSerializer.create()`). Chama `tenants.invites.create_invite(tenant=request.tenant, ...)`. Resposta agora segue o envelope padrão `{"data", "error", "meta"}` (antes retornava o serializer cru, sem envelope) — `meta.invite_sent: true` no 201. Checagem de email duplicado saiu do serializer e virou checagem explícita na view, retornando 409 `USER_EXISTS` (antes: 400 via `ValidationError` do serializer) — decisão necessária para bater com o contrato (`contracts/user-invite-api.md`), que já usava 409 `USER_EXISTS` nesse endpoint no padrão estabelecido por `tenant_users_view`.
- Frontend: `UserFormModal.tsx` perdeu o campo de senha (modo `create`); `useUserMutations.ts` perdeu `password` de `CreateUserInput`; `GerenciarUsuarios.tsx` (não `UsersRoute.tsx` como o `plan.md` supunha — esse é o nome real do componente que consome `UserFormModal`) ganhou tratamento para `USER_EXISTS`/`VALIDATION_ERROR` (erro de `role_id`)/`INVITE_DELIVERY_FAILED` do novo envelope de erro.
- Testes novos em `docuparse-project/backend-core/users/tests/test_user_invites.py` (T008-T011, T016-T017): convite sem senha, rejeição de role de plataforma, 409 em email duplicado, regressão do bug FR-015 (dois tenants, convite vai para `request.tenant` do segundo, não para `Tenant.objects.first()`), ativação completa com login subsequente, token já usado (410) e expirado (410).
- `users/tests/test_user_management.py`: dois testes legados quebrados pela remoção de `password` foram atualizados (`test_create_user_returns_201` sem `password` + lê `r.data["data"]`; `test_create_user_duplicate_email_returns_400` virou `test_create_user_duplicate_email_returns_409`, checando `error.code == "USER_EXISTS"`).
- T018 (US2): nenhuma mudança de código — confirmado que `invite_activate_view`/`activate_invite` já são genéricos por token desde a Fase 2, sem qualquer menção a papel.

## Armadilha ao escrever o teste de regressão FR-015

Não usar `Tenant.objects.order_by("id").first()` para simular "o primeiro tenant do banco" — `Tenant.id` é UUID (`default=uuid.uuid4`), então ordenar por `id` não reflete ordem de criação, é essencialmente aleatório. O bug original usava `Tenant.objects.first()` sem `order_by` explícito, que usa `Tenant.Meta.ordering = ["name"]` (ordem alfabética). O teste correto precisa comparar contra `Tenant.objects.first()` puro (mesmo método do código com bug), não uma ordenação por `id`.

## Verificação

Suíte completa de `backend-core` via `run_script.sh` + `.venv/bin/python -m pytest`: 178 passed, 1 skipped, 0 failed. Frontend: `npx tsc --noEmit` limpo (exit 0).

## Próximos passos

Fase 5 (US3: `POST /api/users/{user_id}/invites/resend/`, rota nova em `users_urls.py`, ação "Reenviar convite" em `UserTable.tsx`) e Fase 6 (Polish: FR-016 em `tenant_users_view`/`TenantUsersPanel.tsx`, rename cleanup em `tenants/tests/test_provisioning.py`).

Ver [[../../docs/specs/019-generalize-tenant-invite/tasks.md|tasks.md]] para o detalhamento completo.
