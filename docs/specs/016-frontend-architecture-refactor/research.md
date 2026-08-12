# Phase 0 Research: Refatoração Arquitetural do Frontend

Todas as decisões abaixo resolvem os pontos técnicos abertos do Technical
Context. Nenhum item ficou como `NEEDS CLARIFICATION` — onde a spec deixou a
escolha explicitamente para o planejamento (ver Assumptions de `spec.md`),
a decisão é registrada aqui.

## 1. Estratégia de migração: strangler fig vs. big-bang

- **Decision**: Migração incremental por fases e por módulo, com o monólito
  `src/main.tsx` e a estrutura nova (`app/modules/shared`) coexistindo até a
  Fase 7.
- **Rationale**: O app está em produção, sem janela de indisponibilidade
  (FR-009/SC-004). Um big-bang rescreveria ~4.630 linhas de uma vez sem rede
  de segurança proporcional. O precedente direto do próprio projeto
  (`docs/specs/008-frontend-ts-migration`) já usou essa estratégia com sucesso
  para a migração JS→TS do mesmo arquivo e documentou explicitamente que a
  quebra estrutural deveria ser um trabalho **futuro e separado** — esta
  feature é esse trabalho.
- **Alternatives considered**: Reescrita paralela completa em branch isolada
  com merge único — rejeitada (risco de divergência prolongada, PR gigante
  impossível de revisar de forma significativa, viola FR-009).

## 2. Ordem de extração de módulos

- **Decision**: `shared/components` → `modules/auth` → roteamento (React
  Router v7) → `modules/documents` (+ TanStack Query) → `modules/operations`
  → `modules/settings` (+ RHF/Zod) → `modules/admin` → `modules/upload`.
- **Rationale**: Ordenado por risco/acoplamento crescente. `shared/components`
  são primitivas de UI já isoladas hoje (`Alert`, `EmptyState`, `Metric`,
  `StatusBadge`, `SearchInput`, `KeyValueGrid`, `Pagination`, `ConfirmDialog`)
  — extração pura, zero risco, desbloqueia todo o resto. `auth` é a peça mais
  coesa do arquivo atual (`AuthContext`/`AuthProvider`/`useAuth`/`LoginPage`).
  Roteamento vem antes de `documents` porque `documents` é o primeiro consumidor
  real de rotas com guarda de permissão. `settings` é deixado por último entre
  os módulos de domínio por ser o maior e mais arriscado (~836 linhas na
  `SettingsView` original + 7 painéis/editores).
- **Alternatives considered**: Extrair por "menor módulo" sem considerar
  acoplamento — rejeitado, pois `documents` depende de padrões (query keys,
  roteamento) que só existem depois da extração de `auth`/roteamento.

## 3. Roteamento — React Router v7

- **Decision**: Modo *data router* (`createBrowserRouter` + `RouterProvider`),
  com uma rota de layout por módulo protegida por `loader`/`element` que
  verifica `hasPermission`, replicando a checagem hoje feita por
  `PermissionGuard` antes de cada `NAV_ITEMS` renderizar.
- **Rationale**: É o modo recomendado pela própria lib para apps com guarda de
  rota e carregamento de dados; mapeia 1:1 os 8 `NAV_ITEMS` atuais em 8 rotas
  (mesmos `permission` codes). O teste de smoke de navegação já existente
  (`src/__tests__/screens.test.tsx`) serve de oráculo direto da migração (deve
  continuar encontrando os mesmos labels de menu para o mesmo conjunto de
  permissões).
- **Alternatives considered**: Modo declarativo (`<Routes>`/`<Route>`)  — mais
  simples, mas não dá suporte nativo a `loader`/error boundary por rota da
  forma exigida por FR-002/FR-007; descartado.

## 4. Camada de dados de servidor — TanStack Query v5

- **Decision**: Um `QueryClient` único em `shared/lib/queryClient.ts`,
  provido em `src/app`. Cada módulo define sua própria fábrica de chaves (ex.
  `documentKeys` em `modules/documents`) e converte hooks existentes: `useDocumentPage`
  (hoje `useState`+`useEffect`+axios) vira `useQuery` parametrizado por
  página/busca/status; `fetchDocumentCount` vira `useQuery` com chave derivada;
  mutações (`handleReprocessDocument`, `handleDeleteDocument`, validação/
  aprovação/rejeição, requeue de DLQ) viram `useMutation` com
  `onSuccess: () => queryClient.invalidateQueries(...)`.
- **Rationale**: FR-003/FR-004 exigem uma camada de consulta centralizada e
  separação de estado de servidor vs. cliente. `useDocumentPage` já é
  praticamente um hook de "query" hoje (parâmetros de página/busca, refetch)
  — a conversão é direta, sem redesenhar o contrato dos componentes que o
  consomem.
- **Alternatives considered**: Manter `useEffect`/`useState` e só adicionar
  cache manual — rejeitado, não atende FR-003/FR-004 nem o anti-padrão listado
  em `frontend_rules.md` ("useEffect para data fetching").

## 5. Estado de cliente — Zustand

- **Decision**: Introduzir Zustand **somente na Fase 4**, depois que TanStack
  Query já assumiu todo o estado de servidor, e apenas para o que sobrar de
  estado de cliente genuíno (ex.: estado de UI local que precise sobreviver
  entre componentes, se identificado durante a extração — hoje o candidato
  mais provável é nenhum, dado que quase todo `useState` atual é ou estado de
  servidor (vira Query) ou estado local de um único componente (permanece
  `useState` local, não precisa de store global)).
- **Rationale**: FR-004 e a regra de `frontend_rules.md` ("never store server
  state in Zustand") — criar slices Zustand antecipadamente, antes de saber o
  que realmente sobra, arrisca duplicar estado de servidor nele.
- **Alternatives considered**: Adotar Zustand desde a Fase 2 para "já ter a
  ferramenta pronta" — rejeitado, incentivaria uso prematuro incorreto.

## 6. Formulários — React Hook Form + Zod

- **Decision**: Introduzir RHF+Zod primeiro no módulo `settings` (Fase 3.6,
  onde há a maior concentração de formulários: OCR/Email/WhatsApp/Integrações/
  Schema/Exemplos), depois em `LoginPage`/registro (Fase 5). Cada formulário
  migrado ganha um `zodResolver` com um schema que espelha exatamente as
  validações manuais já existentes (ex. `password.length >= 8`,
  `password === confirmPassword`), preservando mensagens de erro atuais.
- **Rationale**: FR-005 exige validação declarativa preservando regras/textos
  existentes; `settings` é onde o ganho é maior (muitos inputs controlados
  manualmente) e serve de padrão de referência para os formulários restantes.
- **Alternatives considered**: Migrar `LoginPage` primeiro (mais simples) —
  considerado, mas adiado para depois de `settings` por ser um formulário já
  pequeno e de baixo risco, sem urgência de ser o primeiro.

## 7. ESLint — regras e enforcement de fronteira de módulo

- **Decision**: `@typescript-eslint` (config recomendada + `no-explicit-any`
  como error), `eslint-plugin-react-hooks` (`rules-of-hooks`,
  `exhaustive-deps`), `eslint-plugin-jsx-a11y` (suporte a FR-013/SC-006),
  e um plugin de fronteira de import (`eslint-plugin-boundaries` ou
  configuração equivalente via `no-restricted-imports` com padrão por módulo)
  para bloquear `import ... from '@/modules/X/components/Y'` fora do barrel
  `@/modules/X` (FR-001/FR-008/US2-cenário-4). Regra de tamanho de arquivo via
  `max-lines` (150 para componentes, com override para arquivos de dados/
  tipos que legitimamente são maiores).
- **Rationale**: É a rede de segurança que falta hoje (nenhuma verificação
  automática impede os anti-padrões atuais); implementar antes de qualquer
  refactor estrutural (Fase 0) permite detectar regressão de padrão desde o
  primeiro commit.
- **Alternatives considered**: Adiar ESLint para o final ("depois que tudo
  estiver migrado") — rejeitado; sem ele, nada impede que a própria migração
  reintroduza os anti-padrões que está tentando eliminar.

## 8. Acessibilidade automatizada (WCAG 2.1 AA)

- **Decision**: `eslint-plugin-jsx-a11y` no lint (checagem estática) +
  `vitest-axe` (ou `axe-core` com adaptador Vitest) nos testes de componente,
  executando uma asserção `expect(await axe(container)).toHaveNoViolations()`
  para cada componente migrado, conforme SC-006.
- **Rationale**: Cobre tanto a checagem estática (lint, rápida, roda em todo
  commit) quanto a comportamental (teste, valida o DOM renderizado de fato),
  atendendo FR-013 sem exigir ferramenta manual de auditoria a cada etapa.
- **Alternatives considered**: Auditoria manual (Lighthouse/axe DevTools) por
  etapa — mantida como verificação complementar pontual, mas não como gate
  automatizado por si só (não escalaria a cada módulo extraído).

## 9. Tailwind v3 → v4

- **Decision**: Migração mecânica isolada (Fase 1, antes de qualquer extração
  estrutural): trocar `@tailwind base/components/utilities` em `src/index.css`
  por `@import "tailwindcss"`, mover `theme.extend`/tokens para o novo formato
  CSS-first (`@theme`) ou manter `tailwind.config.ts` no formato compatível
  com o plugin `@tailwindcss/postcss` v4, e atualizar `postcss.config.cjs`.
- **Rationale**: Classes utilitárias hoje usadas no projeto são padrão
  (nenhum uso de sintaxe descontinuada identificado); risco baixo e
  totalmente dissociado da reestruturação de componentes — pode ser validado
  isoladamente por captura visual antes/depois.
- **Alternatives considered**: Migrar Tailwind junto com a extração de cada
  módulo — rejeitado, misturaria duas mudanças (visual/build vs. estrutural)
  no mesmo commit, dificultando isolar a causa de uma eventual regressão.

## 10. React 18 → 19

- **Decision**: Upgrade isolado na Fase 1, junto com `@types/react`/
  `@types/react-dom`, validado por `tsc --noEmit` + `npm run test:run`
  (Vitest + RTL) antes de iniciar qualquer extração de módulo.
- **Rationale**: Inspeção do código atual (`grep` em `main.tsx`) não encontrou
  `defaultProps`, `propTypes`, refs de string ou `ReactDOM.render` legado —
  os padrões que tipicamente quebram no upgrade para React 19 estão ausentes.
  `@testing-library/react` v14 é compatível com React 19 nas versões atuais.
- **Alternatives considered**: Adiar o upgrade para depois da modularização —
  rejeitado; fazer isso cedo, sobre o monólito ainda estável, isola o risco
  do upgrade em si, sem confundi-lo com risco de refactor estrutural.

## 11. Estratégia de branch/PR

- **Decision**: Todo o trabalho ocorre na branch `016-frontend-architecture-refactor`
  (já criada), com um commit por etapa/módulo concluído (cada um com
  `tsc --noEmit` + lint + testes verdes). A integração com `dev`/`staging`/
  `main` segue o fluxo de promoção já em uso no repositório (evidenciado por
  `Merge branch 'dev' into staging` no histórico), via PR(s) abertos quando um
  conjunto coerente de etapas estiver pronto — não é necessário (nem desejável)
  esperar a feature inteira terminar para abrir o primeiro PR.
- **Rationale**: Preserva "sempre entregável" (US4) sem inventar um fluxo de
  branch novo; usa o que o repositório já pratica.
- **Alternatives considered**: Um único PR gigante ao final — rejeitado,
  inviável de revisar e contraria FR-009/US4.
