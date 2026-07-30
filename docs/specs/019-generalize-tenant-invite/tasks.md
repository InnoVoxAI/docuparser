---

description: "Task list for feature 019-generalize-tenant-invite"
---

# Tasks: Convite Direto de Usuários por Tenant Admin

**Input**: Design documents from `docs/specs/019-generalize-tenant-invite/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/user-invite-api.md](./contracts/user-invite-api.md), [quickstart.md](./quickstart.md)

**Tests**: A constituição do projeto (`.specify/memory/constitution.md`, Princípio II) exige testes de integração para fluxos de autenticação/provisionamento — por isso, diferente do padrão "tests opcionais" do template, as tarefas de teste abaixo são **obrigatórias**, não opcionais.

**Organization**: Tarefas agrupadas por história de usuário (US1/US2/US3, prioridades do spec.md). Os dois defeitos pré-existentes trazidos para dentro do escopo (FR-015, FR-016 — ver research.md R3/R4) aparecem como tarefas explícitas e individualmente marcáveis: a correção do FR-015 (tenant errado em `POST /api/users/`) faz parte da própria implementação da US1, já que é o mesmo endpoint sendo reescrito; a correção do FR-016 (tela do operador de plataforma) não pertence a nenhuma das três histórias do spec e aparece na Fase 6 (Polish), no mesmo padrão usado pela feature 017 para ajustes cross-cutting.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: US1, US2 ou US3
- Caminhos de arquivo são relativos à raiz do repositório

---

## Phase 1: Setup

**Purpose**: Preparar o rename do modelo e dos templates de email antes de qualquer lógica de negócio nova

- [X] T001 Gerar a migração Django `RenameModel("TenantAdminInvite", "Invite")` em `docuparse-project/backend-core/tenants/migrations/`, incluindo o rename do `related_name` de `user`/`tenant` (`admin_invites` → `invites`) conforme `data-model.md`
- [X] T002 [P] Renomear os templates de email de `docuparse-project/backend-core/tenants/templates/tenants/emails/admin_invite_subject.txt`/`admin_invite_body.txt` para `invite_subject.txt`/`invite_body.txt`, adicionando a variável `role_display_name` ao texto (research.md R5) — ex.: "Você foi convidado para acessar {{ tenant_name }} como {{ role_display_name }}"

**Checkpoint**: Migração de rename pronta para aplicar; templates de email genéricos por papel.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Generalizar `tenants/invites.py` para emitir/reenviar convite de qualquer papel — toda história de usuário e ambos os bugs corrigidos dependem disso

**⚠️ CRITICAL**: Nenhuma história de usuário pode ser implementada antes desta fase estar completa

- [X] T003 Atualizar todos os imports de `TenantAdminInvite` para `Invite` em `docuparse-project/backend-core/tenants/models.py`, `tenants/invites.py`, `tenants/views.py` e `tenants/tests/test_invites.py`, seguindo o rename de T001
- [X] T004 Implementar `create_invite(tenant: Tenant, name: str, email: str, role: Role) -> Invite` em `docuparse-project/backend-core/tenants/invites.py`: generaliza a lógica hoje em `create_admin_invite` (cria `User` com `set_unusable_password()`, cria `UserProfile` com `role_ref=role`, emite o `Invite` e envia o email usando os templates renomeados de T002 com `role_display_name=role.name`) (depende de T001, T002, T003)
- [X] T005 Reescrever `create_admin_invite(tenant, admin_name, admin_email) -> Invite` em `docuparse-project/backend-core/tenants/invites.py` como wrapper fino sobre `create_invite(tenant, admin_name, admin_email, role=Role.objects.filter(name="admin").first())`, preservando o comportamento existente da feature 017 sem duplicar lógica (depende de T004)
- [X] T006 Implementar `resend_invite(tenant: Tenant, user_id: int) -> Invite` em `docuparse-project/backend-core/tenants/invites.py`: generaliza `resend_admin_invite`, localizando o `UserProfile` por `tenant`+`user_id` (em vez de `role_ref__name="admin"`), levantando `AdminAlreadyActiveError` (renomear para `InviteeAlreadyActiveError` ou manter nome — decisão de implementação) se `user.has_usable_password()`, invalidando qualquer `Invite` `PENDING` do usuário e emitindo um novo via `_issue_invite` (depende de T004)
- [X] T007 Reescrever `resend_admin_invite(tenant) -> Invite` em `docuparse-project/backend-core/tenants/invites.py` como wrapper fino sobre `resend_invite(tenant, user_id=<id do UserProfile com role_ref__name="admin">)`, preservando o contrato existente de `POST /api/admin/tenants/{slug}/invites/resend/` (017) (depende de T006)

**Checkpoint**: `tenants/invites.py` genérico por papel; convite de admin (017) continua funcionando sem alteração de contrato externo.

---

## Phase 3: User Story 1 - Tenant admin convida um usuário diretamente (Priority: P1) 🎯 MVP

**Goal**: O tenant admin informa nome/email/papel de um novo usuário na tela de gestão de usuários do seu tenant e dispara um convite — sem digitar nenhuma senha.

**Independent Test**: Logar como tenant admin, chamar `POST /api/users/` com um email de teste e um `role_id` não-plataforma, e verificar que (a) nenhuma senha é exigida/atribuída, (b) o usuário é criado vinculado ao tenant correto, e (c) um email de convite é enviado.

### Tests for User Story 1

- [ ] T008 [P] [US1] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py` (arquivo novo): `POST /api/users/` sem `password`, com `name`/`email`/`role_id` (role não-plataforma), retorna 201, cria `User` com senha não-utilizável, `UserProfile` vinculado ao `request.tenant` do chamador e ao `role_id` informado, e envia exatamente um email (`django.core.mail.outbox`)
- [ ] T009 [P] [US1] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: `POST /api/users/` com `role_id` de uma role com `is_platform_role=True` retorna 400 `VALIDATION_ERROR`, sem criar usuário
- [ ] T010 [P] [US1] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: `POST /api/users/` com email já em uso retorna 409 `USER_EXISTS`
- [ ] T011 [P] [US1] **Teste de regressão do bug FR-015** em `docuparse-project/backend-core/users/tests/test_user_invites.py`: criar dois tenants (o segundo criado não é `Tenant.objects.first()`), autenticar como tenant admin do **segundo** tenant, chamar `POST /api/users/`, e confirmar que o `UserProfile` do usuário convidado é criado no tenant do chamador (`request.tenant`) — não no primeiro tenant do banco. Sem este teste, o bug documentado em `research.md` R3 poderia voltar silenciosamente

### Implementation for User Story 1

- [ ] T012 [US1] Reescrever `UserCreateSerializer` em `docuparse-project/backend-core/users/serializers.py`: remover o campo `password`; `validate_role_id` passa a rejeitar roles com `is_platform_role=True` (mensagem "Esta role não pode ser atribuída por convite de tenant admin."); `create()` deixa de existir no serializer — a criação passa a ser responsabilidade da view (T013), não mais do serializer, porque agora depende de `request.tenant`
- [ ] T013 [US1] **CORRIGE BUG (FR-015)**: reescrever o branch POST de `users_list_create_view` em `docuparse-project/backend-core/users/user_views.py` para validar o payload com o `UserCreateSerializer` atualizado (T012) e chamar `tenants.invites.create_invite(tenant=request.tenant, name=..., email=..., role=...)` (T004) em vez de `serializer.save()` — **usa `request.tenant` explicitamente**, eliminando o `Tenant.objects.first()` hardcoded que hoje ignora o tenant de quem está autenticado; captura falha de envio de email e retorna 500 `INVITE_DELIVERY_FAILED` sem desfazer a criação (mesma política da 017) (depende de T004, T012)
- [ ] T014 [P] [US1] Remover o campo `password` de `UserFormValues`/`UserFormModal.tsx` (modo `create`) em `docuparse-project/frontend/src/modules/admin/components/UserFormModal.tsx`
- [ ] T015 [US1] Remover `password` de `CreateUserInput` em `docuparse-project/frontend/src/modules/admin/hooks/useUserMutations.ts` e tratar a resposta 400 `role_id` de plataforma / 500 `INVITE_DELIVERY_FAILED` na tela que consome `UserFormModal.tsx` (depende de T014)

**Checkpoint**: Tenant admin consegue convidar um usuário comum do próprio tenant, sem senha, e o usuário vai para o tenant correto — história 1 completa e testável isoladamente.

---

## Phase 4: User Story 2 - Usuário convidado ativa sua conta (Priority: P1)

**Goal**: O convidado usa o link recebido para definir a própria senha; a conta já nasce aprovada e vinculada ao tenant/papel do convite, sem aprovação manual adicional.

**Independent Test**: Gerar um convite de usuário comum (via História 1), acessar o link de ativação, definir uma senha válida, e confirmar login bem-sucedido já com o papel/tenant corretos.

### Tests for User Story 2

- [ ] T016 [P] [US2] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: fluxo completo — convidar usuário (US1), capturar o token do email, `POST` em `/api/admin/tenants/invites/{token}/activate/` com senha válida, confirmar 200, `user.has_usable_password() is True`, `Invite.status == "USED"`, e login subsequente bem-sucedido com o papel/tenant do convite (sem qualquer `is_active` pendente de aprovação)
- [ ] T017 [P] [US2] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: ativação de convite de usuário comum com token já usado retorna 410 `INVITE_ALREADY_USED`; com token expirado retorna 410 `INVITE_EXPIRED` — confirmando que `invite_activate_view`/`activate_invite` (017) continuam funcionando sem nenhuma alteração de código para o caso de papel não-admin (research.md R6)

### Implementation for User Story 2

- [ ] T018 [US2] Nenhuma alteração de código necessária — `invite_activate_view` (`tenants/views.py`) e `activate_invite()` (`tenants/invites.py`, após o rename de T003) já são inteiramente genéricos por token, sem qualquer menção a papel. Esta tarefa existe apenas para registrar explicitamente que T016/T017 são a confirmação formal desse reaproveitamento (depende de T003, T016, T017)

**Checkpoint**: Usuário convidado ativa a conta e loga, já aprovado, sem passar pela aprovação manual do auto-cadastro — histórias 1 e 2 completas em conjunto.

---

## Phase 5: User Story 3 - Reenvio de convite de usuário expirado ou perdido (Priority: P2)

**Goal**: O tenant admin reenvia o convite de um usuário específico quando o link expira ou se perde, sem recriar nada manualmente.

**Independent Test**: Convidar um usuário (US1), deixar o convite expirar (ou marcá-lo como tal em teste), acionar o reenvio pelo `user_id`, e confirmar que o novo link funciona e o anterior não.

### Tests for User Story 3

- [ ] T019 [P] [US3] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: `POST /api/users/{user_id}/invites/resend/` invalida o `Invite` `PENDING` anterior do usuário (`INVALIDATED`) e cria um novo `PENDING` com token/expiração novos
- [ ] T020 [P] [US3] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: reenvio para um `user_id` que pertence a **outro** tenant (não o `request.tenant` do chamador) retorna 404 `USER_NOT_FOUND`, sem revelar que o usuário existe em outro tenant
- [ ] T021 [P] [US3] Teste de integração em `docuparse-project/backend-core/users/tests/test_user_invites.py`: reenvio para um usuário que já ativou a conta (`has_usable_password() is True`) retorna 409 `USER_ALREADY_ACTIVE`

### Implementation for User Story 3

- [ ] T022 [US3] Implementar `user_invite_resend_view` (POST, `require_permission("users.manage")`) em `docuparse-project/backend-core/users/user_views.py`: resolve o `UserProfile` por `user_id` **e** `tenant=request.tenant` (404 se não achar, sem distinguir "não existe" de "existe em outro tenant"), chama `tenants.invites.resend_invite(request.tenant, user_id)` (T006), retorna conforme `contracts/user-invite-api.md` (depende de T006)
- [ ] T023 [US3] Adicionar a rota `users/<int:user_id>/invites/resend/` em `docuparse-project/backend-core/users/users_urls.py`, apontando para `user_invite_resend_view` (depende de T022)
- [ ] T024 [P] [US3] Adicionar a ação "Reenviar convite" (botão + estado de loading/erro, visível apenas para usuários com senha não-utilizável) em `docuparse-project/frontend/src/modules/admin/components/UserTable.tsx`, com `useResendInviteMutation` em `docuparse-project/frontend/src/modules/admin/hooks/useUserMutations.ts`

**Checkpoint**: As três histórias funcionam de forma independente e em conjunto — convite, ativação e reenvio de usuário comum completos.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ajustes que não pertencem a nenhuma das três histórias do spec, mas fazem parte do escopo ampliado desta feature (FR-016) e do fechamento de lacunas deixadas pelo rename

- [ ] T025 **CORRIGE BUG (FR-016)**: reescrever o branch POST de `tenant_users_view` em `docuparse-project/backend-core/tenants/views.py` para chamar `tenants.invites.create_invite(tenant, name, email, role)` (T004) em vez de criar o usuário com a senha em texto vinda do request — **sem** a restrição `is_platform_role=False` (o operador de plataforma pode legitimamente atribuir a role admin/tenantAdmin do tenant, ver research.md R4); `tenant` continua vindo do `slug` da URL (este endpoint não sofre do bug FR-015) (depende de T004)
- [ ] T026 [P] **Teste de regressão FR-016** em `docuparse-project/backend-core/tenants/tests/test_invites.py`: `POST /api/admin/tenants/{slug}/users/` sem `password`, com `role_id` de uma role de plataforma (ex. "admin"), retorna 201 e envia convite por email — confirmando que o operador de plataforma pode atribuir essa role (diferente de US1/FR-003) e que nenhuma senha em texto é mais aceita/exigida (depende de T025)
- [ ] T027 **REMOVER** o campo de senha do formulário "Convidar usuário" em `docuparse-project/frontend/src/modules/admin/components/TenantUsersPanel.tsx` — o rótulo "Convidar" (já existente) passa a corresponder ao comportamento real (depende de T025)
- [ ] T028 [P] Atualizar `docuparse-project/backend-core/tenants/tests/test_invites.py` e `docuparse-project/backend-core/tenants/tests/test_provisioning.py`: substituir todas as referências a `TenantAdminInvite` por `Invite` (rename de T001/T003), sem alterar as asserções de comportamento
- [ ] T029 [P] Rodar o fluxo descrito em `docs/specs/019-generalize-tenant-invite/quickstart.md` manualmente (convidar usuário → capturar convite no console backend → ativar → logar → reenviar) para validar o caminho ponta a ponta
- [ ] T030 [P] Revisar os pontos de log em `docuparse-project/backend-core/tenants/invites.py` após a generalização (T004-T007) para confirmar que nenhum token em claro ou senha é escrito em log, para qualquer papel (FR-013)

**Checkpoint**: Ambos os bugs pré-existentes (FR-015, FR-016) corrigidos e com teste de regressão dedicado; rename de `TenantAdminInvite` → `Invite` completo em código e testes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as histórias de usuário e a Fase 6
- **User Story 1 (Phase 3)**: depende apenas do Foundational
- **User Story 2 (Phase 4)**: depende do Foundational e de US1 (T004) para ter um convite para ativar em teste — na prática, `activate_invite` já existia da 017 e não muda, então US2 é majoritariamente confirmação via teste
- **User Story 3 (Phase 5)**: depende do Foundational (T006) e de US1 (para ter um usuário convidado a quem reenviar)
- **Polish (Phase 6)**: depende do Foundational (T004) — T025-T027 (FR-016) podem rodar em paralelo com US1/US2/US3, já que tocam um endpoint diferente (`tenant_users_view`, não `users_list_create_view`)

### Parallel Opportunities

- T001, T002 (Setup) podem rodar em paralelo
- T008, T009, T010, T011 (testes de US1) podem rodar em paralelo entre si
- T014 (frontend, US1) pode rodar em paralelo com T012/T013 (backend, US1) — arquivos diferentes
- T019, T020, T021 (testes de US3) podem rodar em paralelo entre si
- T025-T027 (FR-016, Polish) podem começar assim que T004 (Foundational) estiver pronto, em paralelo com as fases US1/US2/US3
- T028, T029, T030 (Polish) podem rodar em paralelo entre si

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Setup + Foundational
2. Completar User Story 1 (Phase 3) — tenant admin já consegue convidar um usuário sem senha
3. **Não considerar pronto para produção sem User Story 2** — sem ativação, o convite de US1 é inútil (mesma lógica da 017)

### Incremental Delivery

1. Setup + Foundational → `create_invite`/`resend_invite` genéricos prontos
2. US1 + US2 juntas → primeiro incremento entregável (tenant admin convida, usuário ativa)
3. US3 → reenvio de convite de usuário
4. Polish (FR-016 + rename cleanup) → operador de plataforma para de criar usuário com senha em texto; testes/imports do rename fechados

---

## Notes

- Tarefas marcadas **CORRIGE BUG**/**REMOVER** são as duas correções de defeito pré-existente pedidas explicitamente pelo usuário: T013 (FR-015, dentro de US1 — é o mesmo endpoint sendo reescrito, não faz sentido adiar) e T025/T026/T027 (FR-016, Fase 6 — endpoint do operador de plataforma, fora de qualquer uma das 3 histórias do spec).
- Testes são obrigatórios nesta feature (ver seção **Tests** acima).
- Commitar após cada tarefa ou grupo lógico de tarefas.
- Parar em cada checkpoint para validar a história isoladamente antes de seguir para a próxima.
