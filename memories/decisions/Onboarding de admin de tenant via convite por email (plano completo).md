---
title: Onboarding de admin de tenant via convite por email (plano completo)
type: note
permalink: decisions/tenant-admin-onboarding-invite-flow
tags:
- backend-core
- frontend
- tenants
- auth
- email
- planned
---

# Plano — onboarding de admin de tenant via convite por email

Status: **planejado, não implementado**. Pedido em 2026-07-29; usuário pediu
o plano completo (opção mais complexa, com envio de convite por email),
gerado via speckit. Branch `017-tenant-admin-onboarding`, spec em
`docs/specs/017-tenant-admin-onboarding/` (spec.md, research.md,
data-model.md, contracts/tenant-admin-invite-api.md, tasks.md — 39 tarefas
em 6 fases). Nenhum código foi alterado por este plano ainda.

## Por que isso existe

Ao criar um tenant, o frontend só coletava `slug`+`name`
(`TenantCreateForm.tsx`/`TenantsView.tsx`). O backend
(`tenants/views.py::_provision_tenant`) gerava um admin com email fake
`admin@{slug}` (domínio inválido) e uma senha **compartilhada entre TODOS os
tenants**, vinda da env var `ADMIN_PASSWORD`. O mesmo padrão duplicado existe
em `users/management/commands/seed_data.py` (linha ~135-162). Usuário
perguntou se não seria melhor pedir nome/email reais do admin — na
investigação apareceu o problema maior (senha global compartilhada), o que
motivou ir direto para o plano completo em vez do mínimo viável.

## Achados de pesquisa (research.md) que valem a pena lembrar

- **Nenhuma infra de email reaproveitável existe.** `EmailSettings`/
  `EMAIL_WEBHOOK_URL` (`documents/models.py`, `core/settings.py`) são para
  **ingestão de email de entrada** (parsing de emails recebidos por um
  serviço externo), direção oposta ao que se precisa aqui. `boto3` só é
  usado para S3 (`shared/docuparse_storage/s3.py`), nenhum uso de SES em
  lugar nenhum do monorepo. Não existe `EMAIL_BACKEND` do Django
  configurado, nem SMTP, nem `django-ses`/`anymail`/`djoser`.
- **Decisão de transporte**: `django.core.mail.send_mail` nativo, com
  `EMAIL_BACKEND` configurável por env var — console em dev/test (sem
  exigir provedor externo), SMTP em produção. Não hardcodar decisão de
  provedor (SES/SendGrid) sem confirmação do time.
- **Não existe fluxo de ativação por token em lugar nenhum do sistema.** O
  único precedente de "conta pendente" é `register_view`
  (`users/auth_views.py`), que cria `is_active=False` e espera ativação
  **manual** por um admin via PATCH (`user_views.py`) — sem token, sem link,
  sem email.
- **`is_active` já tem outro significado** (bloqueio administrativo de
  conta, checado explicitamente em `login_view` com mensagem própria) — por
  isso o novo admin é criado com `is_active=True` mas
  `user.set_unusable_password()`, e não com `is_active=False`. Evita
  confundir "aguardando ativar via convite" com "desativado pelo admin".
- **`tenants` é `SHARED_APPS`** (schema público) e `api/admin/tenants/` já é
  roteado como público em `core/urls.py` antes de qualquer resolução de
  tenant — por isso o novo modelo `TenantAdminInvite` e os endpoints
  públicos de ativação não exigem nenhuma mudança de middleware
  multi-tenant.
- **`AUTH_PASSWORD_VALIDATORS` está vazio** hoje no projeto inteiro. Como
  este é o primeiro fluxo onde alguém de fora da equipe define a própria
  senha sem curadoria humana, o plano inclui configurar os validadores
  padrão do Django só para este ponto de entrada (não estende aos fluxos
  internos existentes — ficou registrado como débito técnico separado).

## Decisões de modelagem (data-model.md)

Novo modelo `TenantAdminInvite` (app `tenants`, schema público): `token_hash`
(SHA-256, nunca o token em claro persistido), `status`
(PENDING/USED/INVALIDATED), `expires_at`, `user`/`tenant` FKs. Reenvio de
convite invalida qualquer `PENDING` anterior em vez de deletar (mantém
histórico).

## Tarefas de remoção de código legado (exigência explícita do usuário)

O usuário pediu que a remoção do código antigo aparecesse como itens
individuais e explícitos no tasks.md, não como "cleanup" genérico — ver
`[[speckit-tasks-legacy-removal-explicit]]` como padrão a repetir em specs
futuras. Nesta spec: T015/T016 (remove email fake + exigência de
`ADMIN_PASSWORD` em `_provision_tenant`), T020 (atualiza
`test_provisioning.py`), T036 (`seed_data.py` passa a gerar senha aleatória
por tenant em vez de compartilhar `ADMIN_PASSWORD`), T037 (torna
`ADMIN_PASSWORD` opcional no `docker-compose.yml`, hoje `${ADMIN_PASSWORD:?...}`
obrigatório).

## Próximos passos

MVP em produção exige **US1 (criar tenant com admin real) + US2 (admin ativa
a conta)** juntas — sem US2 o convite gerado por US1 nunca pode ser usado.
US3 (reenvio) e a fase de Polish vêm depois. Implementação ainda não
iniciada; usar `tasks.md` como checklist ao começar.
