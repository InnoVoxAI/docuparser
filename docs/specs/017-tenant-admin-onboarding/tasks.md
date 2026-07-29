---

description: "Task list for feature 017-tenant-admin-onboarding"
---

# Tasks: Onboarding do Administrador de Tenant via Convite por Email

**Input**: Design documents from `docs/specs/017-tenant-admin-onboarding/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/tenant-admin-invite-api.md](./contracts/tenant-admin-invite-api.md), [quickstart.md](./quickstart.md)

**Tests**: A constituição do projeto (`.specify/memory/constitution.md`, Princípio II) exige testes de integração para fluxos de autenticação e para contratos de API — por isso, diferente do padrão "tests opcionais" do template, as tarefas de teste abaixo são **obrigatórias**, não opcionais.

**Organization**: Tarefas agrupadas por história de usuário (US1/US2/US3, prioridades do spec.md). Tarefas de remoção de código legado aparecem como itens explícitos dentro da história a que pertencem (US1) ou na fase final de Polish (quando não pertencem a nenhuma história específica, como o comando de seed local).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: US1, US2 ou US3
- Caminhos de arquivo são relativos à raiz do repositório

---

## Phase 1: Setup

**Purpose**: Configuração de ambiente e infraestrutura básica de email, sem lógica de negócio ainda

- [X] T001 Adicionar as novas variáveis de ambiente com defaults seguros para dev em `docuparse-project/backend-core/core/settings.py`: `EMAIL_BACKEND` (default `django.core.mail.backends.console.EmailBackend`), `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` (default `no-reply@docuparse.local`), `TENANT_ADMIN_INVITE_TTL_HOURS` (default `72`), `FRONTEND_BASE_URL` (default `http://localhost:5173`)
- [X] T002 [P] Configurar `AUTH_PASSWORD_VALIDATORS` em `docuparse-project/backend-core/core/settings.py` com os validadores padrão do Django (`MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`, `UserAttributeSimilarityValidator`), hoje vazio (research.md R6)
- [X] T003 [P] Criar o módulo de serviço `docuparse-project/backend-core/tenants/invites.py` (arquivo novo, vazio além de imports/docstring) que concentrará toda a lógica de convite, mantendo `tenants/views.py` dentro do limite de 400 linhas da constituição

**Checkpoint**: Ambiente configurável para envio de email (console em dev) e critérios mínimos de senha em vigor.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelo de dados e utilitários de convite/email que TODAS as histórias de usuário dependem

**⚠️ CRITICAL**: Nenhuma história de usuário pode ser implementada antes desta fase estar completa

- [X] T004 Criar o modelo `TenantAdminInvite` em `docuparse-project/backend-core/tenants/models.py` (campos `id`, `user` FK, `tenant` FK, `token_hash` único, `status` com choices PENDING/USED/INVALIDATED, `expires_at`, `used_at`, herdando `TimeStampedModel`) conforme `data-model.md`
- [X] T005 Gerar a migração Django para `TenantAdminInvite` em `docuparse-project/backend-core/tenants/migrations/`
- [X] T006 [P] Implementar os helpers de token em `docuparse-project/backend-core/tenants/invites.py`: `generate_invite_token()` (usa `secrets.token_urlsafe(32)`) e `hash_token(token: str)` (SHA-256 hex digest) — o token em claro nunca é persistido (depende de T003)
- [X] T007 [P] Criar os templates de email em `docuparse-project/backend-core/tenants/templates/tenants/emails/admin_invite_subject.txt` e `admin_invite_body.txt`, com o link de ativação montado a partir de `FRONTEND_BASE_URL` + `/ativar-conta/{token}` (token em claro, apenas no email — nunca seria logado ou persistido)
- [X] T008 Implementar `send_admin_invite_email(invite: TenantAdminInvite, admin_email: str, raw_token: str) -> None` em `docuparse-project/backend-core/tenants/invites.py`, usando `django.core.mail.send_mail` com `DEFAULT_FROM_EMAIL` e os templates de T007; deve logar sucesso/falha do envio sem nunca logar o token em claro ou a senha (FR-011) (depende de T001, T007)

**Checkpoint**: Modelo de convite e mecanismo de envio de email prontos para serem usados pelas histórias de usuário.

---

## Phase 3: User Story 1 - Operador cria tenant com administrador real (Priority: P1) 🎯 MVP

**Goal**: Ao criar um tenant, o operador informa nome/email do admin real; o sistema cria a conta sem senha utilizável e dispara o convite — eliminando o email fake e a senha global compartilhada.

**Independent Test**: Criar um tenant via `POST /api/admin/tenants/` com um email de teste real e verificar que (a) o tenant é criado, (b) nenhuma senha utilizável é atribuída, e (c) um email de convite é enviado (visível no console backend em dev).

### Tests for User Story 1

- [X] T009 [P] [US1] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: `POST /api/admin/tenants/` com `admin_name`/`admin_email` cria `Tenant` + `User` (senha não-utilizável) + `UserProfile` (role admin) + `TenantAdminInvite` (status `PENDING`) e envia exatamente um email (verificado via `django.core.mail.outbox` com `locmem` backend nos testes)
- [X] T010 [P] [US1] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: `POST /api/admin/tenants/` com `admin_email` ausente ou inválido retorna 400 `VALIDATION_ERROR` e não cria nenhum `Tenant`/`User`
- [X] T011 [P] [US1] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: `POST /api/admin/tenants/` com `admin_email` já usado por outra conta retorna 409 `ADMIN_EMAIL_IN_USE`

### Implementation for User Story 1

- [X] T012 [US1] Adicionar `admin_name`/`admin_email` ao `TenantCreateSerializer` em `docuparse-project/backend-core/tenants/serializers.py`, validando formato de email e unicidade contra `username`s existentes
- [X] T013 [US1] Implementar `create_admin_invite(tenant, admin_name, admin_email) -> TenantAdminInvite` em `docuparse-project/backend-core/tenants/invites.py`: cria `User` (`username=email`, `email=email`, `first_name=admin_name`, `is_active=True`, `set_unusable_password()`), cria `UserProfile` com `role_ref` = Role "admin", cria `TenantAdminInvite` (`PENDING`, `expires_at = now() + TENANT_ADMIN_INVITE_TTL_HOURS`), chama `send_admin_invite_email` (depende de T004, T006, T008, T012)
- [X] T014 [US1] Reescrever `_provision_tenant` em `docuparse-project/backend-core/tenants/views.py` para chamar `create_admin_invite` com os dados validados; capturar falha no envio do email e retornar 500 `INVITE_DELIVERY_FAILED` **sem** desfazer a criação do tenant/usuário, conforme `contracts/tenant-admin-invite-api.md` (depende de T013)
- [X] T015 [US1] **REMOVER** a geração do email fake do padrão antigo em `_provision_tenant` (`docuparse-project/backend-core/tenants/views.py`, atualmente `tenant_admin_email = f"admin@{slug}"` e o `User.objects.get_or_create` associado) — substituído inteiramente pela chamada a `create_admin_invite` de T014
- [X] T016 [US1] **REMOVER** a exigência da variável de ambiente `ADMIN_PASSWORD` compartilhada em `_provision_tenant` (`docuparse-project/backend-core/tenants/views.py`) — eliminar o `os.environ.get("ADMIN_PASSWORD")` e o branch de erro `ADMIN_PASSWORD_NOT_CONFIGURED`
- [X] T017 [US1] Tratar `ADMIN_EMAIL_IN_USE` (409) em `tenant_list_create_view` em `docuparse-project/backend-core/tenants/views.py`, no mesmo padrão do branch existente `TENANT_EXISTS` (depende de T012)
- [X] T018 [P] [US1] Adicionar os campos `admin_name`/`admin_email` ao formulário em `docuparse-project/frontend/src/modules/admin/components/TenantCreateForm.tsx`
- [X] T019 [US1] Atualizar `handleCreate` em `docuparse-project/frontend/src/modules/admin/components/TenantsView.tsx` para enviar `admin_name`/`admin_email` e exibir as mensagens de erro de `ADMIN_EMAIL_IN_USE`/`VALIDATION_ERROR` (depende de T018)
- [X] T020 [US1] **ATUALIZAR** `docuparse-project/backend-core/tenants/tests/test_provisioning.py`: remover/substituir toda asserção que dependa do padrão antigo (email `admin@{slug}` ou variável `ADMIN_PASSWORD`), adicionando em seu lugar asserções compatíveis com o novo contrato (`admin_name`/`admin_email`, senha não-utilizável, convite pendente criado)

**Checkpoint**: Criar um tenant já produz um admin com email real, sem senha compartilhada, e dispara um convite — história 1 completa e testável isoladamente.

---

## Phase 4: User Story 2 - Administrador convidado ativa sua conta (Priority: P1)

**Goal**: A pessoa convidada usa o link recebido para definir sua própria senha e ativar a conta.

**Independent Test**: Gerar um convite (via História 1), acessar o link, definir uma senha válida, e confirmar login bem-sucedido com essa senha.

### Tests for User Story 2

- [X] T021 [P] [US2] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: fluxo completo — criar tenant, capturar o token do email (via `django.core.mail.outbox` em teste), `POST` no endpoint de ativação com senha válida, verificar 200, `user.has_usable_password() is True`, `invite.status == "USED"`, e login subsequente bem-sucedido
- [X] T022 [P] [US2] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: ativação com token expirado retorna 410 `INVITE_EXPIRED`; com token já usado retorna 410 `INVITE_ALREADY_USED`; com token inexistente retorna 404 `INVITE_NOT_FOUND`
- [X] T023 [P] [US2] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: ativação com senha que viola `AUTH_PASSWORD_VALIDATORS` retorna 400 `VALIDATION_ERROR` e **não** marca o convite como usado

### Implementation for User Story 2

- [X] T024 [US2] Implementar `activate_invite(token: str, password: str) -> User` em `docuparse-project/backend-core/tenants/invites.py`: faz hash do token recebido, busca `TenantAdminInvite` por `token_hash`, valida `status == PENDING` e `expires_at > now()`, valida a senha com `django.contrib.auth.password_validation.validate_password`, define a senha (`user.set_password` + save) e marca o convite `USED` com `used_at = now()` (depende de T004, T006, T002)
- [X] T025 [US2] Implementar `invite_activate_view` (POST, sem autenticação — `authentication_classes([])`, `permission_classes([])`, mesmo padrão de `login_view`) em `docuparse-project/backend-core/tenants/views.py`, retornando 200/400/404/410 conforme `contracts/tenant-admin-invite-api.md` (depende de T024)
- [X] T026 [US2] Adicionar a rota `invites/<str:token>/activate/` em `docuparse-project/backend-core/tenants/urls.py`, apontando para `invite_activate_view` (depende de T025)
- [X] T027 [P] [US2] Criar o módulo de frontend `docuparse-project/frontend/src/modules/tenant-activation/` (`components/ActivateAccountForm.tsx`, `services/tenantActivation.service.ts`, `types.ts`, `index.ts`), seguindo a estrutura de módulo definida em `frontend_rules.md`
- [X] T028 [US2] Implementar `ActivateAccountForm.tsx` com React Hook Form + Zod (campos senha/confirmar senha, estados de loading/erro/sucesso), chamando `tenantActivation.service.ts` (depende de T027)
- [X] T029 [US2] Registrar a rota pública (ex. `/ativar-conta/:token`) do módulo `tenant-activation` no roteador da aplicação, com lazy-loading conforme as regras de módulo de `frontend_rules.md` (depende de T027)

**Checkpoint**: O convidado consegue ativar a conta e logar — histórias 1 e 2 completas e testáveis em conjunto.

---

## Phase 5: User Story 3 - Reenvio de convite expirado ou perdido (Priority: P2)

**Goal**: O operador consegue gerar um novo convite quando o anterior expira ou se perde, invalidando o anterior.

**Independent Test**: Deixar um convite expirar (ou marcá-lo como tal em teste), acionar o reenvio, e confirmar que o novo link funciona e o anterior não.

### Tests for User Story 3

- [ ] T030 [P] [US3] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: reenvio invalida o `TenantAdminInvite` `PENDING` anterior (passa a `INVALIDATED`) e cria um novo `PENDING` com token/expiração novos
- [ ] T031 [P] [US3] Teste de integração em `docuparse-project/backend-core/tenants/tests/test_invites.py`: reenvio para um tenant cujo admin já ativou a conta (`has_usable_password() is True`) retorna 409 `ADMIN_ALREADY_ACTIVE`

### Implementation for User Story 3

- [ ] T032 [US3] Implementar `resend_admin_invite(tenant: Tenant) -> TenantAdminInvite` em `docuparse-project/backend-core/tenants/invites.py`: localiza o `UserProfile` do admin do tenant (role "admin"), retorna erro se `has_usable_password()` já for `True`, invalida qualquer `TenantAdminInvite` `PENDING` existente para esse usuário, cria e envia um novo (depende de T004, T006, T008, T013)
- [ ] T033 [US3] Implementar `invite_resend_view` (POST, `require_permission("tenants.manage")`) em `docuparse-project/backend-core/tenants/views.py` conforme `contracts/tenant-admin-invite-api.md` (depende de T032)
- [ ] T034 [US3] Adicionar a rota `<slug:slug>/invites/resend/` em `docuparse-project/backend-core/tenants/urls.py`, apontando para `invite_resend_view` (depende de T033)
- [ ] T035 [P] [US3] Adicionar a ação "Reenviar convite" (botão + estado de loading/erro) em `docuparse-project/frontend/src/modules/admin/components/TenantsTable.tsx`, com o handler correspondente em `TenantsView.tsx`

**Checkpoint**: Todas as três histórias funcionam de forma independente e em conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ajustes que não pertencem a nenhuma história específica, mas são necessários para não deixar código legado nem lacunas de configuração

- [ ] T036 [P] **AJUSTAR** `docuparse-project/backend-core/users/management/commands/seed_data.py`: remover o padrão compartilhado `f"admin@{t.slug}"` e o reaproveitamento da mesma `ADMIN_PASSWORD` entre tenants (linhas ~135-162); para cada tenant não-default, gerar uma senha aleatória própria (`secrets.token_urlsafe(16)`) e imprimi-la no stdout do comando, mantendo o comando utilizável para seed local/dev sem exigir envio de email real
- [ ] T037 [P] Tornar `ADMIN_PASSWORD` opcional em `docuparse-project/docker-compose.yml` (linha ~135, atualmente `${ADMIN_PASSWORD:?defina ADMIN_PASSWORD no .env...}`), já que deixou de ser exigida pela API de provisionamento e agora só é usada opcionalmente pelo `seed_data.py`
- [ ] T038 Rodar o fluxo descrito em `docs/specs/017-tenant-admin-onboarding/quickstart.md` manualmente (criar tenant → capturar convite no console backend → ativar → logar) para validar o caminho ponta a ponta
- [ ] T039 [P] Revisar todos os pontos de log em `docuparse-project/backend-core/tenants/invites.py` para confirmar que nenhum token em claro ou senha é escrito em log (FR-011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as histórias de usuário
- **User Story 1 (Phase 3)**: depende apenas do Foundational
- **User Story 2 (Phase 4)**: depende do Foundational **e** de T013 (US1) existir, pois a ativação opera sobre convites criados pela criação de tenant — na prática, US2 é testável de forma isolada usando um convite criado diretamente em teste (sem passar pelo endpoint de criação de tenant), mas em produção só faz sentido após US1 estar disponível
- **User Story 3 (Phase 5)**: depende do Foundational e reutiliza `create_admin_invite`/`send_admin_invite_email` de US1 (T013) e a checagem `has_usable_password()` de US2
- **Polish (Phase 6)**: depende de todas as histórias desejadas estarem completas

### Parallel Opportunities

- T001, T002, T003 (Setup) podem rodar em paralelo
- T006, T007 (Foundational) podem rodar em paralelo após T003/T004
- Dentro de cada história, as tarefas de teste marcadas `[P]` podem rodar em paralelo entre si (arquivos/casos diferentes no mesmo arquivo de teste, mas sem dependência umas das outras)
- T018 (frontend, US1) e T012 (backend, US1) podem rodar em paralelo — arquivos diferentes
- T036, T037, T039 (Polish) podem rodar em paralelo

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Setup + Foundational
2. Completar User Story 1 (Phase 3) — já elimina o email fake e a senha compartilhada, mesmo que a ativação ainda não exista (o operador precisaria, temporariamente, reenviar/definir senha manualmente até US2 estar pronta — aceitável apenas como marco intermediário de desenvolvimento, não como entrega final, já que sem US2 o convite nunca pode ser efetivamente usado)
3. **Não considerar a feature pronta para produção sem User Story 2** — sem ela, o convite gerado em US1 é inútil (ver "Why this priority" de US2 no spec.md)

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 + US2 juntas → primeiro incremento entregável em produção (criar tenant com admin real E o admin conseguir ativar a conta)
3. US3 → incremento seguinte (reenvio)
4. Polish → fecha as pontas soltas (seed_data.py, docker-compose.yml, revisão de logs)

---

## Notes

- Testes são obrigatórios nesta feature (ver seção **Tests** acima) — não pular as tarefas de teste mesmo que o template geral do projeto trate testes como opcionais.
- Tarefas marcadas **REMOVER**/**AJUSTAR** em maiúsculas são as tarefas de remoção de código legado exigidas explicitamente: T015, T016 (código de provisionamento), T020 (teste legado), T036 (seed_data.py), T037 (docker-compose.yml).
- Commitar após cada tarefa ou grupo lógico de tarefas.
- Parar em cada checkpoint para validar a história isoladamente antes de seguir para a próxima.
