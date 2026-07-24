---

description: "Task list for feature implementation"

---

# Tasks: Refatoração Arquitetural do Frontend DocuParse (alinhamento a `frontend_rules.md`)

**Input**: Design documents from `docs/specs/016-frontend-architecture-refactor/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/module-boundaries.md](./contracts/module-boundaries.md), [quickstart.md](./quickstart.md)

**Tests**: A suíte de testes automatizados já existe (`docuparse-project/frontend/src/__tests__`, 679 linhas) e é tratada como piso de regressão obrigatório (FR-010) — as tarefas abaixo incluem reforço/expansão de testes onde a spec exige (US1, FR-010, SC-006), mas não geram um ciclo TDD completo por tarefa de refatoração pura (mover código sem mudar comportamento).

**Organization**: Tarefas agrupadas por user story (`spec.md`), na ordem de prioridade P1 → P1 → P2 → P3. Como esta é uma migração estrutural (não CRUD), a User Story 2 concentra o grosso do trabalho técnico (extração módulo a módulo); User Stories 1, 3 e 4 têm tarefas próprias e verificáveis independentemente, mas também são reforçadas por checkpoints embutidos na User Story 2 (referenciados explicitamente).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story à qual a tarefa pertence (US1–US4)
- Caminhos de arquivo sempre relativos a `docuparse-project/frontend/`

## Path Conventions

Projeto único já existente: `docuparse-project/frontend/src/`. Nenhum novo
projeto/pacote é criado; a estrutura-alvo (`src/app`, `src/modules/*`,
`src/shared/*`) é criada dentro do pacote atual (ver `plan.md` → Project
Structure).

---

## Phase 1: Setup

**Purpose**: Preparar dependências e baseline antes de qualquer mudança estrutural.

- [X] T001 Rodar o gate completo sobre o estado atual (`npm run typecheck && npm run test:run && npm run build` em `docuparse-project/frontend`) e registrar como baseline "verde" pré-migração
  - **Resultado (2026-07-24)**: `typecheck` PASS · `build` PASS · `test:run` **NÃO** verde — 27/28 passam, 1 falha pré-existente e reproduzível de forma consistente (3/3 execuções), não causada por nenhuma mudança desta feature (nenhum código-fonte foi tocado antes deste gate, apenas `npm install`).
    - Teste: `src/__tests__/flows.test.tsx > Upload > envia um documento manual e mostra a confirmação`.
    - Causa raiz identificada por depuração isolada (script standalone fora da suíte): o `axios.post` com corpo `FormData` contra uma instância com `baseURL` relativo, interceptado pelo MSW (`XMLHttpRequestInterceptor`) sob jsdom + Node 22, **nunca resolve nem rejeita** — trava indefinidamente (reproduzido também fora do componente `UploadView`, isolando `axios`+`FormData`+MSW+jsdom como a combinação problemática, não a lógica de `UploadView`). Não é flakiness de timing; é um hang determinístico.
    - **Decisão (usuário, 2026-07-24)**: investigação/correção adiada para depois — apenas documentar. Baseline pré-migração aceito como 27/28 verde, com esta falha conhecida registrada como débito pré-existente. Ao rodar o "gate completo" em qualquer etapa futura da Fase 4+ (T018, T020, T025, T032, T035, T039, T041, T042, T046) e na Fase 5/7, este teste específico deve continuar sendo a única falha esperada — qualquer falha adicional é regressão real introduzida pela migração. Se ao mexer em `modules/upload` (T042) o comportamento de upload for tocado, esta falha deve ser revisitada/corrigida naquele ponto, não ignorada.
- [X] T002 [P] Adicionar dependências de produção ao `docuparse-project/frontend/package.json`: `react-router`, `@tanstack/react-query`, `@tanstack/react-query-devtools`, `zustand`, `react-hook-form`, `zod`, `@hookform/resolvers`
- [X] T003 [P] Adicionar dependências de desenvolvimento ao `docuparse-project/frontend/package.json`: `eslint`, `@typescript-eslint/parser`, `@typescript-eslint/eslint-plugin`, `eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`, `eslint-plugin-boundaries`, `prettier`, `vitest-axe`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Rede de segurança (lint/testes) e esqueleto da estrutura-alvo — bloqueia todas as user stories.

**⚠️ CRITICAL**: Nenhuma extração de módulo (US2) pode começar antes desta fase.

- [X] T004 Criar `docuparse-project/frontend/eslint.config.js` com `@typescript-eslint` (recomendado + `no-explicit-any` como error), `react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps`, `jsx-a11y` recomendado, e regra `max-lines` (150, override para arquivos de dados/tipos) — ver `research.md` §7
  - **Resultado (2026-07-24)**: Config plano ESLint 9 criado. `react-hooks` restrito às 2 regras nomeadas pela tarefa (`rules-of-hooks`/`exhaustive-deps`), não ao preset `recommended` completo (v7.1.1 do plugin inclui regras experimentais adicionais fora do escopo pedido). Override de `max-lines` estendido a arquivos de teste (`**/__tests__/**`, `**/*.test.{ts,tsx}`) além de dados/tipos — FR-012/SC-002 limitam apenas "arquivo de componente", não specs. `npm run lint` sobre o `src/` atual (monólito ainda intacto) reporta 33 erros/11 avisos pré-existentes em `main.tsx`/`types.ts` (16 `no-explicit-any`, 11 `exhaustive-deps` warn, 14 `jsx-a11y`, 1 `no-unused-vars`, 1 `no-empty`, 1 `max-lines` no próprio `main.tsx`) — nenhum é regressão desta tarefa; são débito pré-existente a resolver durante a extração módulo a módulo (Fase 4) e o endurecimento de lint (Fase 5/T047, escopado a "código migrado"). A regra de fronteira de módulo (`eslint-plugin-boundaries`) fica para T047 (Fase 5), conforme o próprio enunciado desta tarefa não a menciona.
- [X] T005 [P] Criar `docuparse-project/frontend/.prettierrc` e adicionar scripts `lint`/`format` em `docuparse-project/frontend/package.json`
  - **Resultado (2026-07-24)**: `.prettierrc` alinhado ao estilo já usado no código (sem `;`, aspas simples, indentação 4, trailing commas). Scripts `lint` (`eslint .`) e `format` (`prettier --write .`) adicionados. `npm run format` **não** foi executado sobre o repo inteiro (reformataria `main.tsx` em massa, fora do escopo desta tarefa) — apenas validado com `--check` sobre os arquivos novos desta fase.
- [X] T006 [P] Configurar threshold de cobertura ≥80% por diretório de módulo em `docuparse-project/frontend/vitest.config.ts` (aplicado progressivamente conforme módulos forem extraídos — ver `data-model.md` "Cobertura de teste")
  - **Resultado (2026-07-24)**: Adicionada entrada `'src/modules/**'` (80% linhas/statements/branches/functions) ao mapa `thresholds` do provider v8 (suporta glob por diretório nativamente), mantendo os limiares globais existentes (piso de regressão do monólito) intocados.
- [X] T007 Criar esqueleto de pastas vazio: `docuparse-project/frontend/src/app/`, `docuparse-project/frontend/src/modules/`, `docuparse-project/frontend/src/shared/{components,hooks,lib,types,utils}` (ver `plan.md` → Project Structure)
- [X] T008 Mover as 3 instâncias axios (`api`, `authApi`, `comApi`) e o interceptor JWT de `docuparse-project/frontend/src/main.tsx` para `docuparse-project/frontend/src/shared/lib/http.ts`; atualizar `main.tsx` para importar de lá
  - **Resultado (2026-07-24)**: Interceptor JWT movido de um `useEffect` de attach/eject dentro de `AuthProvider` para o escopo do módulo em `http.ts` (anexado uma única vez à criação das instâncias). Comportamento idêntico preservado: `attachToken` já lia o token do `localStorage` a cada requisição, sem depender de estado React, e `AuthProvider` só monta uma vez por sessão do app — logo o attach/eject por ciclo de vida era supérfluo. `tsc --noEmit` limpo após a mudança.
- [X] T009 [P] Criar `docuparse-project/frontend/src/shared/lib/queryClient.ts` (instância `QueryClient`, ainda não consumida por nenhum componente)
- [X] T010 Upgrade React 18→19 em `docuparse-project/frontend/package.json` (+ `@types/react`, `@types/react-dom`) — commit isolado; rodar gate completo (T001) antes de prosseguir
  - **Resultado (2026-07-24)**: `react`/`react-dom` 18→19.2.8, `@types/react`/`@types/react-dom` 18→19. Instalado com `--legacy-peer-deps` (peer `react-dom@^18` de `@testing-library/react@14` é aviso esperado e aceito — ver research.md §10: v14 é compatível com React 19 na prática). Gate completo (T001: typecheck+test:run+build) verde — 27/28 testes, mesma falha pré-existente documentada em T001, nenhuma regressão nova.
- [X] T011 Migrar Tailwind v3→v4: `docuparse-project/frontend/src/index.css` (`@import "tailwindcss"`), `docuparse-project/frontend/tailwind.config.js`→`.ts`, `docuparse-project/frontend/postcss.config.cjs` — commit isolado; rodar gate completo + checklist visual (`quickstart.md`) antes de prosseguir
  - **Resultado (2026-07-24)**: `tailwindcss`+`@tailwindcss/postcss` 4.3.3 instalados; `postcss.config.cjs` usa só o plugin `@tailwindcss/postcss` (autoprefixing interno ao v4); `index.css` usa `@import "tailwindcss"` + `@config "../tailwind.config.ts"` (mantém `content`/`theme.extend` explícitos, sem uso de sintaxe descontinuada — confirma research.md §9); `tailwind.config.js`→`.ts` (tipado via `satisfies Config`), adicionado a `tsconfig.node.json` para cobertura de typecheck do editor. **Efeito colateral encontrado e corrigido**: a reinstalação de dependências (React 19 + Tailwind v4, ambas via `--legacy-peer-deps`) des-hoisteou `@testing-library/dom` (antes no root `node_modules/`, virou aninhado só sob `@testing-library/react`), quebrando `@testing-library/user-event` (`ERR_MODULE_NOT_FOUND`) em 4 arquivos de teste. Corrigido declarando `@testing-library/dom` como devDependency explícita (`^9.3.4`, mesma versão já resolvida) — prática padrão para projetos que usam `user-event` diretamente. Gate completo verde após a correção: typecheck limpo, build OK (CSS de saída validado — classes `.primary-button`/`.success-button`/`.danger-button` compilam com os mesmos valores visuais via variáveis CSS do v4), 27/28 testes (mesma falha pré-existente, sem regressão). **Checklist visual manual (`quickstart.md`) não foi percorrido em navegador** — sem ferramenta de screenshot/browser disponível neste ambiente; validação limitada à inspeção estrutural do CSS gerado. Recomenda-se passe visual manual pelo usuário antes do commit desta etapa.

**Checkpoint**: Fundação pronta — rede de segurança ativa, esqueleto de pastas criado, dependências novas instaladas, upgrades de React/Tailwind validados isoladamente.

---

## Phase 3: User Story 1 - Preservação total do comportamento durante toda a transição (Priority: P1) 🎯 MVP

**Goal**: Garantir que a suíte de testes automatizados e o checklist de regressão manual cubram hoje todas as telas, servindo de oráculo confiável para todas as etapas seguintes.

**Independent Test**: Rodar `npm run test:run` e confirmar que cada uma das 10 telas (Login, Dashboard, Inbox, Validação, Aprovados, Rejeitados, Operações, Configurações, Usuários, Roles) tem pelo menos um teste de fumaça passando; percorrer manualmente o checklist de `quickstart.md` sobre o estado atual.

### Implementation for User Story 1

- [ ] T012 [US1] Auditar `docuparse-project/frontend/src/__tests__/screens.test.tsx` e demais specs em `docuparse-project/frontend/src/__tests__/` e listar quais das 10 telas não têm teste de fumaça próprio
- [ ] T013 [US1] Adicionar os testes de fumaça faltantes identificados em T012, um arquivo por tela em `docuparse-project/frontend/src/__tests__/`
- [ ] T014 [US1] Revisar e ajustar o checklist de regressão manual em `docs/specs/016-frontend-architecture-refactor/quickstart.md` com qualquer lacuna encontrada em T012/T013
- [ ] T015 [US1] Executar o checklist de regressão manual completo (`quickstart.md`) sobre o estado atual (baseline pré-extração) e registrar o resultado como referência de comparação para as próximas fases

**Checkpoint**: User Story 1 entregável isoladamente — rede de regressão reforçada, útil mesmo sem nenhuma extração estrutural ainda ter começado.

---

## Phase 4: User Story 2 - Arquitetura-alvo disponível e verificável (Priority: P1)

**Goal**: Extrair o monólito `src/main.tsx` para `src/app` + `src/modules/*` + `src/shared/*`, com roteamento real (React Router v7), camada de consulta centralizada (TanStack Query), formulários declarativos (RHF+Zod) e, apenas onde sobrar, estado de cliente em Zustand.

**Independent Test**: Inspecionar `docuparse-project/frontend/src/` e confirmar: nenhum arquivo concentra múltiplas telas não relacionadas; navegação por rotas reais; busca de dados via camada de consulta centralizada; import direto de arquivo interno de outro módulo é sinalizado pelo lint.

### 4a. `shared/components` (primitivas de UI — extração pura, zero risco)

- [ ] T016 [P] [US2] Extrair `Alert`, `EmptyState`, `Field`, `Metric` de `docuparse-project/frontend/src/main.tsx` para `docuparse-project/frontend/src/shared/components/`
- [ ] T017 [P] [US2] Extrair `SearchInput`, `StatusBadge`, `KeyValueGrid`, `Pagination`, `ConfirmDialog` de `docuparse-project/frontend/src/main.tsx` para `docuparse-project/frontend/src/shared/components/`
- [ ] T018 [US2] Atualizar `docuparse-project/frontend/src/main.tsx` para importar essas primitivas de `docuparse-project/frontend/src/shared/components` (remover definições locais); rodar gate completo (T001) + checklist visual (`quickstart.md`); commit da etapa

### 4b. `modules/auth`

- [ ] T019 [US2] Criar `docuparse-project/frontend/src/modules/auth/{context.tsx,components/LoginPage.tsx,components/PermissionGuard.tsx,types.ts,index.ts}` movendo `AuthContext`/`AuthProvider`/`useAuth`/`LoginPage`/`PermissionGuard`/`AcessoNaoAutorizado` de `src/main.tsx`
- [ ] T020 [US2] Atualizar `docuparse-project/frontend/src/main.tsx` para consumir `modules/auth` apenas pelo barrel `index.ts` (ver `contracts/module-boundaries.md`); rodar gate completo + checklist visual; commit da etapa
- [ ] T021 [P] [US2] Adicionar teste de acessibilidade (`vitest-axe`, ver `quickstart.md`) para `LoginPage` em `docuparse-project/frontend/src/modules/auth/__tests__/LoginPage.a11y.test.tsx` (SC-006)

### 4c. Roteamento (React Router v7)

- [ ] T022 [US2] Criar `docuparse-project/frontend/src/app/router.tsx` com `createBrowserRouter` (modo data router), uma rota por item de `NAV_ITEMS` atual, guarda de permissão via `useAuth().hasPermission` (ver `research.md` §3, `data-model.md` "Rota")
- [ ] T023 [US2] Criar `docuparse-project/frontend/src/shared/components/ErrorBoundary.tsx` (classe, `componentDidCatch`, fallback amigável) e associar como `errorElement` de cada rota de módulo em `router.tsx` (FR-007)
- [ ] T024 [US2] Substituir a alternância `activeView`/switch de `App` em `src/main.tsx` pelo router; criar `docuparse-project/frontend/src/app/main.tsx` (bootstrap com `RouterProvider` + `QueryClientProvider`)
- [ ] T025 [US2] Ajustar `docuparse-project/frontend/src/__tests__/screens.test.tsx` apenas nos seletores de navegação (URLs), sem alterar labels/permissões testados; rodar gate completo + checklist visual; commit da etapa

### 4d. `modules/documents` (+ TanStack Query)

- [ ] T026 [US2] Criar `docuparse-project/frontend/src/modules/documents/hooks/queryKeys.ts` com `documentKeys` (ver `data-model.md`)
- [ ] T027 [US2] Converter `useDocumentPage` (hoje em `src/main.tsx`) em `useDocumentsQuery` baseado em `useQuery` em `docuparse-project/frontend/src/modules/documents/hooks/useDocumentsQuery.ts`, preservando a assinatura de retorno (`page,setPage,search,setSearch,data,loading,error,refresh`) consumida pelas telas
- [ ] T028 [P] [US2] Converter `fetchDocumentCount` em `useQuery` própria (chave `documentKeys.count`) em `docuparse-project/frontend/src/modules/documents/hooks/useDocumentCount.ts`
- [ ] T029 [US2] Converter as mutações (`handleReprocessDocument`, `handleDeleteDocument`, validação/aprovação/rejeição) em `useMutation` com `invalidateQueries` em `onSuccess`, em `docuparse-project/frontend/src/modules/documents/hooks/useDocumentMutations.ts`
- [ ] T030 [P] [US2] Mover `Dashboard`, `InboxView`, `ApprovedView`, `RejectedView`, `ValidationView`, `DocumentTable`, `ExtractedFieldsModal`, `RejectedDocumentModal`, `LangExtractPanel`, `DocumentMetadataPanel`, `FieldVersionHistoryModal` de `src/main.tsx` para `docuparse-project/frontend/src/modules/documents/components/`
- [ ] T031 [US2] Expor `docuparse-project/frontend/src/modules/documents/index.ts` (`DocumentsRoutes`, hooks, `documentKeys`) conforme `contracts/module-boundaries.md`
- [ ] T032 [US2] Atualizar `router.tsx` para consumir `DocumentsRoutes`; remover código correspondente de `src/main.tsx`; rodar gate completo + checklist visual; commit da etapa
- [ ] T033 [P] [US2] Adicionar testes de acessibilidade para `DocumentTable` e `ValidationView` em `docuparse-project/frontend/src/modules/documents/__tests__/`

### 4e. `modules/operations` (DLQ)

- [ ] T034 [US2] Criar `docuparse-project/frontend/src/modules/operations/{hooks,components,types.ts,index.ts}` convertendo `OperationsView` e as chamadas de DLQ (summary/events/requeue) para `useQuery`/`useMutation`
- [ ] T035 [US2] Atualizar `router.tsx` para consumir `OperationsRoutes`; remover código de `src/main.tsx`; rodar gate completo + checklist visual; commit da etapa

### 4f. `modules/settings` (+ React Hook Form + Zod)

- [ ] T036 [P] [US2] Criar schemas Zod espelhando as validações manuais atuais de cada aba (OCR/Email/WhatsApp/Integrações) em `docuparse-project/frontend/src/modules/settings/schemas/`
- [ ] T037 [US2] Dividir `SettingsView` original em subcomponentes ≤150 linhas por aba (`OcrSettingsPanel`, `EmailSettingsPanel`, `WhatsAppSettingsPanel`, `IntegrationSettingsPanel`) em `docuparse-project/frontend/src/modules/settings/components/`, cada um usando `useForm` + `zodResolver`
- [ ] T038 [P] [US2] Mover `SchemaFieldsEditor`, `ExamplesEditor`, `ReferenceDocumentPanel`, `SchemaList`, `DeleteSchemaModal`, `ConfigList` para `docuparse-project/frontend/src/modules/settings/components/`
- [ ] T039 [US2] Converter busca de schemas/layouts para `useQuery` (`settingsKeys`, análogo a `documentKeys`); expor `docuparse-project/frontend/src/modules/settings/index.ts`; atualizar `router.tsx`; remover código de `src/main.tsx`; rodar gate completo + checklist visual; commit da etapa
- [ ] T040 [P] [US2] Adicionar testes de acessibilidade para os painéis de Configurações migrados em `docuparse-project/frontend/src/modules/settings/__tests__/`

### 4g. `modules/admin`

- [ ] T041 [US2] Criar `docuparse-project/frontend/src/modules/admin/` movendo `GerenciarUsuarios`/`GerenciarRoles` de `src/main.tsx`, convertendo fetch/mutations para TanStack Query; expor barrel; atualizar `router.tsx`; rodar gate completo + checklist visual; commit da etapa

### 4h. `modules/upload`

- [ ] T042 [US2] Criar `docuparse-project/frontend/src/modules/upload/` movendo `UploadView` de `src/main.tsx`; expor barrel; atualizar `router.tsx`; rodar gate completo + checklist visual; commit da etapa

### 4i. Zustand residual, formulários restantes e remoção final do monólito

- [ ] T043 [US2] Revisar o estado remanescente após T016–T042; criar slice(s) Zustand apenas para estado de cliente genuíno identificado (`docuparse-project/frontend/src/shared/store/` ou dentro do módulo específico) — ver `research.md` §5; pular esta tarefa se nada restar
- [ ] T044 [P] [US2] Converter `LoginPage` (login/registro) para `react-hook-form` + `zodResolver` em `docuparse-project/frontend/src/modules/auth/components/LoginPage.tsx`, preservando mensagens/regras de validação atuais (FR-005)
- [ ] T045 [US2] Formalizar `docuparse-project/frontend/src/shared/utils/errorMessages.ts` a partir de `readError`/`asApiError`; aplicar em todos os error boundaries e telas migradas (FR-007)
- [ ] T046 [US2] Remover `docuparse-project/frontend/src/main.tsx` (monólito original, já vazio após T018–T045); confirmar `docuparse-project/frontend/src/app/main.tsx` (T024) como único bootstrap; rodar gate completo + checklist visual; commit da etapa

**Checkpoint**: User Story 2 completa — arquitetura-alvo integralmente implantada, `src/main.tsx` não existe mais.

---

## Phase 5: User Story 3 - Rede de segurança que impede reintrodução de anti-padrões (Priority: P2)

**Goal**: Ativar e comprovar que o lint bloqueia os anti-padrões identificados, incluindo a fronteira de módulo (que só é totalmente significativa com os módulos da Fase 4 já existindo).

**Independent Test**: Introduzir deliberadamente uma violação de cada regra-chave e confirmar que `npm run lint` reporta erro.

### Implementation for User Story 3

- [ ] T047 [US3] Habilitar a regra de fronteira de módulo (`eslint-plugin-boundaries`, configurada em `docuparse-project/frontend/eslint.config.js`) apontando para `src/modules/*` criados na Fase 4; rodar `npm run lint` e confirmar zero violações reais no código migrado
- [ ] T048 [P] [US3] Introduzir deliberadamente um import direto de arquivo interno de outro módulo (fora do barrel) e confirmar que `npm run lint` falha; reverter a alteração sem commitá-la
- [ ] T049 [P] [US3] Introduzir deliberadamente um `any` não justificado e confirmar que `npm run lint` falha; reverter a alteração sem commitá-la
- [ ] T050 [US3] Adicionar `npm run lint`, `npm run typecheck` e `npm run test:run` como gate obrigatório no pipeline de CI do frontend (respeitando o caminho frontend-only já existente desde o commit `a6c2235`)

**Checkpoint**: Rede de segurança verificada e conectada ao CI — anti-padrões bloqueados automaticamente antes do merge.

---

## Phase 6: User Story 4 - Evolução incremental, sempre entregável (Priority: P3)

**Goal**: Confirmar, ao final, que toda a transição ocorreu em etapas pequenas e entregáveis, sem exigir indisponibilidade nem deixar estado quebrado em nenhum ponto intermediário.

**Independent Test**: Revisar o histórico de commits da branch `016-frontend-architecture-refactor` e confirmar que cada etapa de extração teve commit próprio com gate completo verde.

### Implementation for User Story 4

- [ ] T051 [US4] Revisar o histórico de commits desta branch e confirmar que cada etapa das Fases 2–5 (T010, T011, T018, T020, T025, T032, T035, T039, T041, T042, T046, T047) foi um commit isolado com gate completo verde, sem nenhum commit "big-bang"
- [ ] T052 [US4] Documentar no(s) PR(s) (ver `research.md` §11) a sequência de entrega incremental realizada, referenciando os checkpoints de cada sub-fase

**Checkpoint**: Todas as user stories concluídas e verificadas independentemente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Fechamento — itens que afetam a feature como um todo, não uma story específica.

- [ ] T053 [P] Atualizar `docs/specs/016-frontend-architecture-refactor/quickstart.md` com qualquer ajuste descoberto durante a execução das Fases 2–6
- [ ] T054 Reavaliar os escapes `[key: string]: any`/`unknown` em `docuparse-project/frontend/src/shared/types/` e nos tipos `DlqStream`/`DlqEvent`, apertando o que for estável (mantendo índice permissivo só onde o payload é legitimamente heterogêneo)
- [ ] T055 Rodar `npm run build` de produção final em `docuparse-project/frontend` e validar o bundle/preview local
- [ ] T056 Executar o checklist de regressão visual completo (`quickstart.md`) uma última vez, ponta a ponta, sobre a estrutura final

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — **bloqueia** todas as user stories
- **User Story 1 (Phase 3)**: depende apenas do Foundational; pode ser entregue isoladamente (MVP mínimo: rede de regressão reforçada, sem nenhuma extração estrutural)
- **User Story 2 (Phase 4)**: depende do Foundational; suas sub-fases internas (4a→4i) são **sequenciais** entre si (não paralelizáveis como um todo — `documents` depende de `auth`+roteamento já extraídos, `settings` referencia `documents`, etc. — ver `research.md` §2)
- **User Story 3 (Phase 5)**: depende da Phase 4 estar completa (a regra de fronteira de módulo só é significativa com os módulos já existindo); a configuração *básica* de lint (T004) já roda desde a Phase 2
- **User Story 4 (Phase 6)**: depende de todas as fases anteriores estarem concluídas (é uma verificação retrospectiva do processo)
- **Polish (Phase 7)**: depende de todas as user stories desejadas estarem completas

### Within Phase 4 (User Story 2)

- 4a (`shared/components`) → 4b (`auth`) → 4c (roteamento) → 4d (`documents`) → 4e (`operations`) → 4f (`settings`) → 4g (`admin`) → 4h (`upload`) → 4i (Zustand/RHF-Zod restante/limpeza final)
- Dentro de cada sub-fase, tarefas marcadas `[P]` (ex. T016/T017, T028/T030, T036/T038) tocam arquivos diferentes e podem ser feitas em paralelo; a tarefa de integração final de cada sub-fase (ex. T018, T032, T039) depende de todas as `[P]` daquela sub-fase estarem prontas.

### Parallel Opportunities

- Setup: T002 e T003 em paralelo
- Foundational: T005, T006, T009 em paralelo (após T004/T007/T008)
- User Story 1: T012 antes de T013; T013/T014 podem ocorrer em paralelo depois
- User Story 2, por sub-fase: ver marcações `[P]` acima (T016/T017; T028/T030; T036/T038)
- User Story 3: T048 e T049 em paralelo (violações independentes)

---

## Parallel Example: Sub-fase 4a (`shared/components`)

```bash
# Extração das primitivas de UI pode ocorrer em paralelo (arquivos diferentes):
Task: "Extrair Alert, EmptyState, Field, Metric para src/shared/components/"
Task: "Extrair SearchInput, StatusBadge, KeyValueGrid, Pagination, ConfirmDialog para src/shared/components/"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (crítico — bloqueia tudo)
3. Completar Phase 3: User Story 1
4. **PARAR e VALIDAR**: rede de regressão reforçada já é um incremento de valor entregável isoladamente, mesmo sem nenhuma extração estrutural

### Incremental Delivery (recomendado)

1. Setup + Foundational → fundação pronta
2. User Story 1 → rede de regressão reforçada → entregar/demo
3. User Story 2, sub-fase por sub-fase (4a→4i) → cada uma entregável isoladamente (commit + gate verde), conforme US4
4. User Story 3 → lint de fronteira de módulo ativo e verificado no CI
5. User Story 4 → fechamento/documentação do processo incremental
6. Polish → limpeza final

### Notes

- `[P]` = arquivos diferentes, sem dependência entre si
- Rodar o gate completo (`npm run typecheck && npm run lint && npm run test:run && npm run build`, ver `quickstart.md`) ao final de cada tarefa de integração marcada acima — não avançar com gate vermelho
- Commit por etapa/sub-fase concluída, nunca por "toda a Phase 4 de uma vez"
- Evitar: mover e reescrever ao mesmo tempo — mover primeiro preservando comportamento, só então melhorar
