# Refatoração Arquitetural do Frontend DocuParse (016)

Rascunho de descrição de PR — gerado pela tarefa T052 (Fase 6). Ainda **não**
publicado (branch `016-frontend-architecture-refactor` não enviada ao remoto
nesta sessão, por decisão do usuário). Copiar o conteúdo abaixo ao abrir o PR.

## Resumo

Migra o frontend DocuParse do monólito `src/main.tsx` (~5450 linhas) para a
arquitetura-alvo descrita em `frontend_rules.md`: `src/app` (bootstrap/shell) +
`src/modules/*` (auth, documents, operations, settings, admin, upload) +
`src/shared/*` (componentes/hooks/lib/types/utils comuns), com roteamento real
(React Router v7), camada de consulta centralizada (TanStack Query),
formulários declarativos (React Hook Form + Zod) e lint de fronteira de módulo
bloqueante no CI. `src/main.tsx` não existe mais.

Ver `docs/specs/016-frontend-architecture-refactor/spec.md` para os
requisitos originais e `tasks.md` para o detalhamento completo de cada etapa
(nota "Resultado" por tarefa).

## Sequência de entrega incremental (US4)

A migração inteira ocorreu em commits pequenos e isolados, cada um com o gate
completo verde (`typecheck && lint && test:run && build`) antes de avançar —
nunca um commit "big-bang" cobrindo mais de uma sub-fase. Auditoria completa
do histórico em T051.

| Commit | Fase/sub-fase | O que entrega |
|---|---|---|
| `225ae88` | Fase 1 (Setup) | Dependências novas (router/query/form) + tooling de lint/format |
| `125e788` | Fase 2 (Foundational) | ESLint/Prettier/cobertura, esqueleto de pastas, `http.ts`/`queryClient.ts`, **upgrades React 19 + Tailwind v4** |
| `29d88a6` | Fase 3 (US1) | Testes de fumaça para Aprovados/Rejeitados — rede de regressão reforçada antes de qualquer extração |
| `86585ae` | 4a — `shared/components` | Extração pura das primitivas de UI (Alert, EmptyState, Field, Metric, SearchInput, StatusBadge, KeyValueGrid, Pagination, ConfirmDialog) |
| `8322754` | 4b — `modules/auth` | `AuthContext`/`AuthProvider`/`LoginPage`/`PermissionGuard` extraídos + teste de acessibilidade |
| `156ff46` | 4c — Roteamento | React Router v7 real substitui o switch de `activeView`; `ErrorBoundary` por rota |
| `42d9c9e` | 4d — `modules/documents` | Dashboard/Inbox/Aprovados/Rejeitados/Validação + TanStack Query (queries/mutations) |
| `cba0358` | 4e — `modules/operations` | Painel DLQ convertido para TanStack Query |
| `9c55ef4` | 4f — `modules/settings` | Abas de configuração convertidas para React Hook Form + Zod |
| `20e01cd` | 4g — `modules/admin` | Gerenciar Usuários/Roles + TanStack Query |
| `e68a841` | 4h — `modules/upload` | Extração da tela de Upload (sem estado de servidor próprio) |
| `0a585b2` | 4i — Fechamento da Fase 4 | Revisão Zustand (nada a fazer), `LoginPage` em RHF+Zod, `errorMessages.ts` aplicado, `TenantsView` migrada, **remoção final de `src/main.tsx`** |
| `52988e8` | Fase 5 (US3) | `eslint-plugin-boundaries` bloqueante + gate de CI dedicado ao frontend (`frontend-ci.yaml`) |

Cada linha da tabela corresponde a um checkpoint documentado no próprio
`tasks.md` (seção da sub-fase) com o resultado do gate completo registrado na
nota "Resultado" da tarefa de integração daquela etapa.

### Observação sobre T010/T011

As tarefas T010 (upgrade React 18→19) e T011 (upgrade Tailwind v3→v4) pediam
"commit isolado" cada uma, mas ambas foram entregues dentro do commit único
de Fase 2 (`125e788`), junto com T004–T009. O gate completo ficou verde antes
de cada upgrade ser incorporado (documentado nas notas "Resultado" de T010/T011
em `tasks.md`), então o requisito de segurança (nunca avançar com gate
vermelho) foi respeitado — só o requisito de granularidade do commit em si não
foi seguido à risca nesse ponto específico. Não houve necessidade de reverter
ou corrigir retroativamente; registrado aqui apenas para transparência do
histórico.

## Como revisar

- `docs/specs/016-frontend-architecture-refactor/tasks.md` — histórico
  completo, tarefa por tarefa, com notas de resultado/decisões de arquitetura.
- `docs/specs/016-frontend-architecture-refactor/contracts/module-boundaries.md`
  — regras de fronteira entre módulos aplicadas pelo lint (T047).
- `docuparse-project/frontend/src/modules/*/index.ts` — superfície pública de
  cada módulo (único ponto de importação permitido de fora do módulo).

## Teste

- `npm run typecheck && npm run lint && npm run test:run && npm run build`
  (mesmo gate rodado a cada commit da tabela acima).
- Checklist de regressão manual: `docs/specs/016-frontend-architecture-refactor/quickstart.md`.
