---

description: "Task list for Migração do Frontend DocuParse para TypeScript"
---

# Tasks: Migração do Frontend DocuParse de JavaScript/JSX para TypeScript/TSX

**Input**: Design documents from `docs/specs/008-frontend-ts-migration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/frontend-types-and-test-surface.md, quickstart.md

**Tests**: INCLUÍDOS E OBRIGATÓRIOS — a spec exige uma suíte automatizada (FR-024/FR-025; clarify Q1=C) cobrindo telas, integrações e permissões.

**Organization**: Agrupadas por user story (US1–US4). Ordem de execução: Setup → Foundational → US2 (infra de tipos) → US1 (rede de testes/regressão) → US3 (tipagem) → US4 (strict).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1–US4 (apenas nas fases de story)

## Path Conventions

Pacote único em `docuparse-project/frontend/`. Caminhos relativos à raiz do repositório.

⚠️ **Conflito de arquivo dominante**: `docuparse-project/frontend/src/main.tsx` é o monólito (~4047 linhas) tocado por quase todas as tarefas de tipagem → **essas tarefas são sequenciais entre si** (não `[P]`). Já os arquivos de teste (`src/__tests__/*`), os `src/models/**` e os arquivos de config são distintos → permitem `[P]`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Instalar TypeScript e a stack de testes; criar configs; sem renomear código de aplicação ainda.

- [X] T001 Adicionar `typescript` (~5.4) a `devDependencies` e os scripts `typecheck` (`tsc --noEmit`) e `build` (`tsc --noEmit && vite build`) em `docuparse-project/frontend/package.json`
- [X] T002 [P] Criar `docuparse-project/frontend/tsconfig.json` permissivo (`allowJs:true`, `checkJs:false`, `strict:false`, `jsx:"react-jsx"`, `moduleResolution:"bundler"`, `noEmit:true`, `paths: {"@/*":["./src/*"]}`) (research D2)
- [X] T003 [P] Criar `docuparse-project/frontend/tsconfig.node.json` (composite) incluindo `vite.config.ts`
- [X] T004 [P] Criar `docuparse-project/frontend/src/vite-env.d.ts` com `ImportMetaEnv` (`VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN`, `VITE_BACKEND_CORE_URL`, `VITE_BACKEND_COM_URL`, opcionais) (data-model.md)
- [X] T005 Adicionar a stack de testes a `devDependencies` (`vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, `msw`, `@vitest/coverage-v8`) e os scripts `test`/`test:run`/`coverage` em `docuparse-project/frontend/package.json` (research D4)
- [X] T006 [P] Garantir `.dockerignore` (já criado) e que `typescript`+libs de teste entrem antes do `npm install` da imagem; sem mudar Dockerfile/compose (research D7)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Renomear arquivos para TS/TSX em modo permissivo e estabelecer baseline verde. BLOQUEIA todas as user stories.

**⚠️ CRITICAL**: Concluir antes de qualquer fase de story.

- [X] T007 [P] Renomear via `git mv` os 15 arquivos `docuparse-project/frontend/src/models/**/*.js` → `.ts` (schemas, prompts, rules, examples dos 4 tipos documentais)
- [X] T008 Renomear via `git mv` `docuparse-project/frontend/src/main.jsx` → `src/main.tsx` e atualizar `docuparse-project/frontend/index.html` (`<script src="/src/main.tsx">`)
- [X] T009 [P] Renomear `docuparse-project/frontend/vite.config.js` → `vite.config.ts` (manter proxy `/api`,`/com` e alias `@`) e adicionar bloco `test` do Vitest (`environment:"jsdom"`, `globals:true`, `setupFiles`)
- [X] T010 Estabelecer baseline verde: rodar `npm run typecheck` com config permissiva e neutralizar erros remanescentes com `any`/`// @ts-expect-error` temporários **sem alterar lógica**, em `docuparse-project/frontend/src/main.tsx`
- [X] T011 [P] Criar scaffolding de teste: `docuparse-project/frontend/src/__tests__/setup.ts` (import `@testing-library/jest-dom`; ciclo `beforeAll/afterEach/afterAll` do MSW) e `src/__tests__/mocks/handlers.ts` (handlers MSW espelhando os endpoints do contrato)

**Checkpoint**: App roda com `.tsx`/`.ts` (JS/TS coexistindo), `typecheck` passa em modo permissivo, infra de teste pronta.

---

## Phase 3: User Story 2 - Validação estática de tipos e build funcional (Priority: P1)

**Goal**: Checagem de tipos executável e efetiva; build de produção e dev server funcionais pelos scripts atuais.

**Independent Test**: Rodar `typecheck` e `build` (ambos concluem); introduzir um erro de tipo proposital e confirmar que `typecheck` o reporta.

- [X] T012 [US2] Validar `npm run typecheck` concluindo sem erros bloqueantes e `npm run build` (`tsc --noEmit && vite build`) gerando bundle, a partir de `docuparse-project/frontend/`
- [X] T013 [P] [US2] Teste de efetividade da checagem: documentar/automatizar a verificação de que um erro de tipo deliberado é detectado por `tsc --noEmit` (SC-003) — registrar em `docuparse-project/frontend/src/__tests__/typecheck.md` (ou script de verificação)
- [X] T014 [US2] Validar dev/Docker: `docker compose build --no-cache frontend` + `up -d --force-recreate --renew-anon-volumes frontend` + `curl http://localhost:5173/` (200) e proxy `/api/ocr/health` (200) (quickstart)

**Checkpoint**: Pipeline de tipos e build operacional (valor de negócio da iniciativa entregue).

---

## Phase 4: User Story 1 - Preservação total do comportamento (Priority: P1) 🎯 MVP

**Goal**: Garantir, por suíte automatizada + checklist, que telas, fluxos, navegação, permissões e integrações permanecem idênticos.

**Independent Test**: `npm run test:run` 100% verde cobrindo telas/permissões/integrações; checklist de regressão completo sem divergências visuais/funcionais.

### Tests for User Story 1 ⚠️ (rede de regressão — base da preservação)

- [X] T015 [P] [US1] Testes de render/smoke de todas as telas (Login, Dashboard, Inbox, Validação, Aprovados, Rejeitados, Operações, Configurações, Usuários, Roles) em `docuparse-project/frontend/src/__tests__/screens.test.tsx`
- [X] T016 [P] [US1] Testes de permissões: visibilidade de `NAV_ITEMS` por `user.permissions` e gating de `PermissionGuard`/`AcessoNaoAutorizado`, em `docuparse-project/frontend/src/__tests__/permissions.test.tsx`
- [X] T017 [P] [US1] Testes de integração de auth (login persiste tokens + seta user; `/me` restaura; logout limpa) com MSW, em `docuparse-project/frontend/src/__tests__/auth.test.tsx`
- [X] T018 [P] [US1] Testes de integração da Validação (extração; editar/remover/adicionar campo; **Salvar** 201/409/422; **Histórico** somente leitura; aprovar/rejeitar) com MSW, em `docuparse-project/frontend/src/__tests__/validation.test.tsx`
- [ ] T019 [P] [US1] Testes de integração de Inbox/Rejeitados/Configurações/Operações (listagem+busca, reprocessar/excluir, salvar settings, DLQ) com MSW, em `docuparse-project/frontend/src/__tests__/flows.test.tsx`

### Implementação / verificação

- [X] T020 [US1] Ajustar `handlers.ts` (MSW) para refletir exatamente os endpoints/params/payloads do contrato e fazer toda a suíte passar (`npm run test:run`), em `docuparse-project/frontend/src/__tests__/mocks/handlers.ts`
- [ ] T021 [US1] Executar o checklist de regressão manual do `quickstart.md` (visual + funcional + Network) e registrar evidência; corrigir qualquer divergência **sem alterar comportamento**

**Checkpoint**: Rede de regressão automatizada verde + checklist OK — preservação comprovada (MVP de segurança).

---

## Phase 5: User Story 3 - Base tipada do domínio e componentes (Priority: P2)

**Goal**: Tipos explícitos para domínio, contextos, props e DTOs de integração.

**Independent Test**: Inspecionar o código e confirmar tipos de domínio/contexto/props/DTOs; alterar um uso de DTO de forma incompatível gera erro de tipo.

- [X] T022 [P] [US3] Criar `docuparse-project/frontend/src/types.ts` com domínio + DTOs (`ExtractionField`/`FieldsMap`, `ExtractionResult`, `ExtractionFieldVersion`, `DocumentStatus`, `Document`, `User`, `AuthContextValue`, `FieldRow`, `SaveMessage`, `ActiveView`) (data-model.md)
- [X] T023 [P] [US3] Tipar os exports de `docuparse-project/frontend/src/models/**/*.ts` (`SchemaField[]`, `isLikely*Text`, `*PromptForDocumentType`)
- [X] T024 [US3] Tipar o núcleo transversal em `docuparse-project/frontend/src/main.tsx`: `AuthContext`/`AuthProvider`/`useAuth` (usar `AuthContextValue`/`User`), as 3 instâncias axios e `readError`
- [X] T025 [US3] Tipar props (incluindo children, callbacks, eventos React) dos componentes utilitários e de domínio em `docuparse-project/frontend/src/main.tsx` (`Alert`, `Field`, `StatusBadge`, `DocumentTable`, `LangExtractPanel`, `ValidationView`, modais, etc.)
- [X] T026 [US3] Tipar telas e `App`/`Root`, estados não triviais (`useState<...>`) e estruturas de formulário em `docuparse-project/frontend/src/main.tsx`
- [X] T027 [US3] Aplicar DTOs aos acessos de API via generics do axios (`api.get<Document[]>`, `api.put<ExtractionFieldVersion>`, etc.) em `docuparse-project/frontend/src/main.tsx`, sem alterar endpoints/payloads (contrato)

**Checkpoint**: Domínio, contextos, props e integrações tipados; erros de uso de DTO são detectados.

---

## Phase 6: User Story 4 - Evolução incremental e endurecimento até strict (Priority: P3)

**Goal**: Subir o rigor por etapas até `strict: true` com zero erros bloqueantes, mantendo o app funcional.

**Independent Test**: Em estados intermediários, app compila/roda com JS+TS; ao final, `strict:true` ativo, `typecheck` sem erros bloqueantes e suíte verde.

- [X] T028 [US4] Ativar `noImplicitAny` e corrigir, em `docuparse-project/frontend/tsconfig.json` + `src/main.tsx` (manter app rodando e suíte verde)
- [X] T029 [US4] Ativar `strictNullChecks` e corrigir (tratar `| null`/opcionais) em `docuparse-project/frontend/tsconfig.json` + `src/main.tsx`
- [X] T030 [US4] Ativar `strict: true` completo e remover `// @ts-expect-error`/`any` temporários onde viável; `any` remanescente deve ser **pontual e documentado** (FR-010), em `docuparse-project/frontend/tsconfig.json` + `src/main.tsx`
- [X] T031 [US4] Desligar `allowJs` (todos os `models/**` já em `.ts`) em `docuparse-project/frontend/tsconfig.json` e confirmar `typecheck` verde

**Checkpoint**: Configuração estrita atingida; aplicação e testes íntegros.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T032 [P] Atingir as metas de cobertura (`npm run coverage`): fluxos críticos (auth/validação/permissões) ≥ 90%, demais ≥ 80% (research D5)
- [ ] T033 [P] Remover dead code/imports não usados e `any` injustificados; garantir consistência de terminologia (Constituição I/III) em `docuparse-project/frontend/src/main.tsx`
- [ ] T034 Revalidar Docker (`build --no-cache` + `up --renew-anon-volumes`) e executar o checklist de regressão final do `quickstart.md`
- [ ] T035 [P] Atualizar `docuparse-project/frontend/TYPESCRIPT_MIGRATION.md` e `README` (se houver) com o estado final (scripts `typecheck`/`test`, config estrita)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as stories (rename + baseline).
- **US2 (Phase 3)**: depende da Foundational. Entrega a infra de validação/build (P1).
- **US1 (Phase 4)**: depende da Foundational + infra de teste (T011) e idealmente de US2. Entrega a rede de regressão (P1, MVP de segurança).
- **US3 (Phase 5)**: depende da Foundational; a tipagem deve ocorrer com a rede de testes (US1) já no lugar para detectar regressões.
- **US4 (Phase 6)**: depende de US3 (não há como atingir `strict` sem a tipagem do domínio/props/DTOs).
- **Polish (Phase 7)**: depende das stories desejadas concluídas.

### Conflitos de arquivo (sequencialidade obrigatória)

- `src/main.tsx`: T008 → T010 → T024 → T025 → T026 → T027 → T028 → T029 → T030 → T033 (sequencial).
- `tsconfig.json`: T002 → T028 → T029 → T030 → T031 (sequencial).
- `package.json`: T001 → T005 (sequencial).
- `__tests__/mocks/handlers.ts`: T011 → T020.

### Parallel Opportunities

- Setup: T002, T003, T004, T006 em paralelo (arquivos distintos); T001→T005 sequenciais (mesmo `package.json`).
- Foundational: T007 (models) e T009 (vite.config) e T011 (tests scaffolding) em paralelo; T008→T010 sequenciais (main.tsx).
- US1: T015–T019 em paralelo (arquivos de teste distintos); T020 depende deles; T021 por último.
- US3: T022 e T023 em paralelo; T024–T027 sequenciais (mesmo `main.tsx`).
- Polish: T032, T033, T035 em paralelo.

---

## Parallel Example: User Story 1

```bash
# Suíte de regressão — arquivos de teste distintos, em paralelo:
Task: "screens.test.tsx — render de todas as telas"
Task: "permissions.test.tsx — gating por permissão"
Task: "auth.test.tsx — login/me/logout com MSW"
Task: "validation.test.tsx — salvar/histórico/aprovar com MSW"
Task: "flows.test.tsx — inbox/rejeitados/settings/DLQ com MSW"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) + Phase 2 (Foundational): TS habilitado, código renomeado, baseline verde, infra de teste.
2. Phase 3 (US2): typecheck + build funcionais (valor imediato).
3. Phase 4 (US1): rede de regressão automatizada + checklist → **preservação comprovada** (MVP de segurança).
4. **PARAR e VALIDAR**: app idêntico, testes verdes, build OK.

### Incremental Delivery

1. Setup + Foundational → base TS/coexistência.
2. US2 → checagem de tipos + build (demo).
3. US1 → suíte de regressão verde (demo — segurança).
4. US3 → domínio/contextos/props/DTOs tipados (demo).
5. US4 → `strict` total (demo final).

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente.
- A maior parte da tipagem incide em `main.tsx` (sequencial) — paralelize via arquivos de teste e configs.
- **Nunca** alterar lógica/endpoints/payloads durante a migração (FR-016–FR-019); usar `any`/`@ts-expect-error` temporários como ponte.
- `any` final apenas pontual e documentado (FR-010/SC-007).
- Commit por task ou grupo lógico; cada etapa deixa o app compilando e executável (SC-009).
