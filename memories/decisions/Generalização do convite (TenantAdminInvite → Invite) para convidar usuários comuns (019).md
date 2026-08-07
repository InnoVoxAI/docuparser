---
title: Generalização do convite (TenantAdminInvite → Invite) para convidar usuários
  comuns (019)
type: note
permalink: decisions/generalize-tenant-invite-019
tags:
- backend-core
- frontend
- tenants
- users
- auth
- email
- planned
---

# Plano — convite direto de usuário comum pelo tenant admin (019)

Status: **planejado, não implementado**. Pedido em 2026-07-29, na sequência
direta da [[Onboarding de admin de tenant via convite por email (plano completo)|017]]
(já mesclada). Usuário perguntou "o que acha de generalizar o convite da 017
para usuários comuns, mantendo o auto-cadastro existente" — plano completo
gerado via speckit. Branch `019-generalize-tenant-invite`, spec em
`docs/specs/019-generalize-tenant-invite/` (spec.md, research.md,
data-model.md, contracts/user-invite-api.md, plan.md, quickstart.md).
Nenhum código alterado ainda — apenas planejamento.

## Por que isso existe

Hoje só existem dois caminhos de entrada de usuário: (a) auto-cadastro
(`register_view`, usuário escolhe `tenant_slug`, fica `is_active=False` até
aprovação manual do tenant admin) e (b) criação direta pelo tenant admin via
`POST /api/users/` (`UserFormModal.tsx` → `users_list_create_view`), que hoje
exige que o **tenant admin digite uma senha em texto** para o novo usuário —
o mesmo anti-padrão que motivou a 017 (só que ali era senha compartilhada
entre tenants; aqui é senha inventada por outra pessoa e comunicada fora de
banda). A pergunta original era se dava para reaproveitar a infraestrutura de
convite da 017 em vez de duplicar um segundo mecanismo de token/expiração.

## Achado principal: o modelo já é genérico, só faltava o nome

`TenantAdminInvite` (`tenants/models.py:75-98`) não tem **nenhum campo**
específico de admin — o papel do convidado já é resolvido e gravado em
`UserProfile.role_ref` **antes** de o registro de convite existir
(`create_admin_invite`, `tenants/invites.py`). Ou seja, generalizar não exige
schema novo: só um `RenameModel` `TenantAdminInvite` → `Invite` (migração
única, schema público, sem `migrate_schemas --tenant`).

## Bug pré-existente encontrado durante a investigação

`UserCreateSerializer.create()` (`users/serializers.py:121-135`, usado por
`users_list_create_view` POST) faz `tenant = Tenant.objects.first()` **em vez
de** `request.tenant` (que o próprio branch GET da mesma view já usa
corretamente, linha 51). Ou seja, hoje, se um tenant admin de um tenant que
não é o primeiro criado no banco cria um usuário pela tela de gestão, o novo
usuário é silenciosamente associado ao **tenant errado**. Vira correção
obrigatória da 019 (não dá pra emitir convite de usuário certo sem saber o
tenant certo) — ver `research.md` R3. Task de regressão explícita prevista
(criar usuário como admin de um tenant que não é o primeiro do banco,
confirmar tenant correto).

## Decisões de modelagem/generalização (research.md)

- `resend_admin_invite(tenant)` assumia "o admin do tenant" via
  `role_ref__name="admin"` — não serve para usuário comum, onde um tenant
  pode ter vários convites pendentes ao mesmo tempo. Generalizado para
  `resend_invite(tenant, user_id)`; o reenvio de admin (017) vira caso
  particular chamando essa versão com o `user_id` do admin.
- `activate_invite()` (ativação pública por token) já é 100% genérico — zero
  mudança de rota ou lógica, só o import do model renomeado.
- Achado relacionado, **fora de escopo**: `TenantUsersPanel.tsx` (tela do
  *operador de plataforma*, permissão `tenants.manage`, não do tenant admin)
  já rotula seu form como "Convidar" mas cria usuário com senha em texto sem
  enviar convite nenhum — mesmo anti-padrão, ator diferente (fora do spec
  desta feature, registrado para não esquecer, não misturado nesta entrega).

## Próximos passos

Ainda falta `/speckit-tasks` (quebrar plan.md em tasks.md) e a implementação.
Usar `tasks.md` como checklist ao começar — seguir o padrão já estabelecido
de tasks de remoção/rename explícitas (ver [[speckit-tasks-legacy-removal-explicit]]).
