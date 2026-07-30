---
title: '019 - Generalize Tenant Invite: Fase 1/2 (Setup + Foundational)'
type: note
permalink: docuparser/features/019-generalize-tenant-invite-fase-1-2-setup-foundational
tags:
- feature-019
- tenants
- invites
---

## Status

Fases 1 (Setup) e 2 (Foundational) da feature `019-generalize-tenant-invite` implementadas (T001-T007). User stories (US1/US2/US3) e Fase 6 (Polish, FR-016) ainda **não** implementadas.

## O que mudou

- `TenantAdminInvite` renomeado para `Invite` em `docuparse-project/backend-core/tenants/models.py`, via migração `tenants/migrations/0006_rename_tenantadmininvite_to_invite.py` (`RenameModel` + `AlterField` para os `related_name` `admin_invites` → `invites`). `related_name` mudou tanto em `user` quanto em `tenant`.
- Templates de email renomeados: `admin_invite_subject.txt`/`admin_invite_body.txt` → `invite_subject.txt`/`invite_body.txt`, com nova variável de contexto `role_display_name` (= `role.name`) e `invitee_name` (antes `admin_name`).
- `tenants/invites.py` generalizado:
  - `create_invite(tenant, name, email, role) -> Invite`: função genérica nova. `create_admin_invite` agora é wrapper fino que resolve `role=Role.objects.filter(name="admin").first()` e delega.
  - `resend_invite(tenant, user_id) -> Invite`: localiza `UserProfile` por `tenant`+`user_id` (não mais `role_ref__name="admin"`). `resend_admin_invite(tenant)` agora é wrapper fino.
  - `AdminAlreadyActiveError` renomeado para `InviteeAlreadyActiveError` (decisão tomada durante a implementação, já que a task deixava a escolha em aberto) — `tenants/views.py` atualizado para importar/capturar o novo nome. O texto do erro HTTP (`ADMIN_ALREADY_ACTIVE`) não mudou, só o nome da exceção Python.
- `activate_invite` inalterado (já era genérico).

## Decisão de implementação não coberta pela task original

`create_invite` precisa tolerar `role=None` (usa `role.name if role else ""` ao montar o email) — **não** é opcional no sentido de "role pode faltar por design", é para preservar compatibilidade com `tenants/tests/test_provisioning.py::TenantListCreateTests::test_create_tenant_returns_201_with_slug`, que cria um tenant sem pré-popular a Role "admin" no banco de teste. Antes da generalização isso não importava (o nome da role nunca era lido). Sem esse guard, o teste quebrava com 500 (`AttributeError: 'NoneType' object has no attribute 'name'`). Ver [[decisions/invite-role-none-guard]] se essa nota for criada depois.

## Verificação

Suíte completa de `backend-core` rodada via `run_script.sh` + `.venv/bin/python -m pytest`: 171 passed, 1 skipped (teste que exige Postgres real via `tenant_db` marker), 0 failed.

## Próximos passos

Fases 3-6 do `tasks.md` (US1: `POST /api/users/` sem senha + correção do bug FR-015 do `Tenant.objects.first()`; US2: confirmação de ativação; US3: reenvio por `user_id`; Polish: FR-016 no `tenant_users_view` do operador de plataforma).

Ver [[../../docs/specs/019-generalize-tenant-invite/tasks.md|tasks.md]] para o detalhamento completo.
