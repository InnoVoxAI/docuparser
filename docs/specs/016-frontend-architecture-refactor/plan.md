# Implementation Plan: Refatoração Arquitetural do Frontend DocuParse (alinhamento a `frontend_rules.md`)

**Branch**: `016-frontend-architecture-refactor` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/016-frontend-architecture-refactor/spec.md`

## Summary

O frontend (`docuparse-project/frontend`) é hoje um monólito de ~4.630 linhas em
`src/main.tsx` (~90 declarações de topo, ~15 telas, sem router, sem camada de
dados centralizada, sem formulários declarativos, sem ESLint) rodando em
produção (Cloudflare Pages + Docker). O objetivo é migrar, sem big-bang e sem
janela de indisponibilidade, para a arquitetura descrita em
`docuparse-project/frontend/frontend_rules.md`: React 19, TypeScript strict,
Tailwind v4, React Router v7, TanStack Query v5, Zustand, React Hook Form +
Zod, estrutura `src/app` + `src/modules/*` (com barrel `index.ts`) +
`src/shared/*`, componentes ≤150 linhas, error boundaries por rota, testes por
camada com cobertura ≥80% no código migrado, e conformidade WCAG 2.1 AA por
componente migrado.

Abordagem técnica: **strangler fig incremental**. (1) Construir rede de
segurança (ESLint + Prettier + reforço da suíte de testes existente) antes de
tocar em estrutura. (2) Fazer os upgrades de dependência (React 19, Tailwind
v4) isolados, sobre o monólito ainda intacto. (3) Criar o esqueleto
`app/modules/shared` vazio. (4) Extrair módulo por módulo do monólito na ordem
de menor para maior risco/acoplamento (shared/components → auth → roteamento
→ documents com TanStack Query → operations → settings com RHF+Zod → admin →
upload), cada extração encolhendo `main.tsx` e mantendo os testes existentes
verdes. (5) Introduzir Zustand só para o estado de cliente genuíno remanescente
após a adoção de TanStack Query. (6) Endurecer lint final e eliminar
`main.tsx`.

## Technical Context

**Language/Version**: TypeScript 5.4+ em modo `strict` (já ativo hoje, mantido
durante toda a migração); React 18.2 → **React 19** (upgrade na Fase 1, sem
uso prévio de `defaultProps`/`propTypes`/string refs — risco baixo confirmado
por inspeção do código atual).

**Primary Dependencies**: Existentes — `axios`, `lucide-react`, `clsx`,
`tailwind-merge`, Vite 5, Tailwind 3.4 → **Tailwind v4**. Novas — `react-router`
v7 (modo *data router*, `createBrowserRouter`), `@tanstack/react-query` v5 (+
`@tanstack/react-query-devtools` em dev), `zustand`, `react-hook-form`, `zod`,
`@hookform/resolvers`. Novas (dev/qualidade) — `eslint`, `@typescript-eslint/*`,
`eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y` (acessibilidade, FR-013),
um plugin de fronteira de módulo (`eslint-plugin-boundaries` ou equivalente,
para bloquear import cross-module fora do barrel, FR-001/FR-008), `prettier`,
`vitest-axe` (ou `axe-core` + wrapper para Vitest, para SC-006).

**Storage**: N/A — nenhuma mudança de armazenamento; o frontend continua
consumindo os mesmos endpoints (`/api/ocr`, `/api/auth`, `/com/api/v1`) sem
alteração de contrato (FR-011).

**Testing**: Vitest + React Testing Library + MSW (já em uso, 679 linhas em
`src/__tests__` cobrindo auth/flows/pagination/permissions/screens/validation)
— **piso de regressão**, nunca reduzido. Adicionar: cobertura mínima ≥80% para
código migrado/extraído (`@vitest/coverage-v8`, já presente, com threshold por
diretório de módulo); testes de acessibilidade automatizados por componente
migrado (`vitest-axe`).

**Target Platform**: Navegador, 320–1920px (constituição III); deploy via
Cloudflare Pages (branch `main`→prod, outras→staging, conforme
`vite.config.ts`) e Docker Compose (dev local), inalterados por esta feature.

**Project Type**: Aplicação web — este feature é **frontend-only**
(`docuparse-project/frontend`); backend (`backend-core` Django, `backend-ocr`
FastAPI, `backend-com`) não é tocado (FR-011).

**Performance Goals**: Sem regressão perceptível de performance percebida pelo
usuário em relação ao estado atual (SC-001); nenhum novo orçamento numérico de
performance é exigido pela constituição especificamente para o frontend além
do já vigente (responsividade 320–1920px).

**Constraints**: Zero regressão funcional/visual a cada etapa (SC-001); nenhum
arquivo de componente >150 linhas ao final, exceções pontuais justificadas em
código (FR-012/SC-002); cobertura ≥80% no código migrado (FR-010); WCAG 2.1 AA
por componente migrado (FR-013/SC-006); nenhuma mudança de contrato de API
(FR-011); sem janela de indisponibilidade dedicada (FR-009/SC-004); sem
reescrita paralela — o monólito e os módulos extraídos devem coexistir e
funcionar a cada etapa (US4).

**Scale/Scope**: 1 arquivo monólito (~4.630 linhas, ~90 declarações de topo) a
decompor em ~8 unidades de organização (`shared`, `modules/auth`,
`modules/documents`, `modules/operations`, `modules/settings`,
`modules/admin`, `modules/upload`, `app`); ~15 telas; suíte de testes atual de
679 linhas como piso.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio / Seção | Avaliação | Justificativa |
|---|---|---|
| I. Code Quality (arquivos ≤400 linhas, funções ≤50 linhas, TS preferido, lint zero violações, sem código morto) | **PASS** (reforça) | Esta feature *introduz* o gate de lint que hoje não existe e define um limite ainda mais estrito (150 linhas/componente) do que o piso da constituição (400 linhas/arquivo) — não há enfraquecimento, só reforço. |
| II. Testing Standards (cobertura ≥80% features novas, isolamento de teste, sem chamada de rede em unit test) | **PASS** | FR-010 fixa ≥80% para código migrado, mesmo piso da constituição. Suíte existente (MSW, sem rede real) é preservada como base. |
| III. UX Consistency (estados async explícitos, mensagens amigáveis, WCAG 2.1 AA, responsivo 320–1920px, terminologia consistente) | **PASS** | FR-006, FR-007 e FR-013/SC-006 cobrem exatamente esses pontos; nenhuma tela nova é criada, apenas reorganizada, preservando terminologia atual. |
| IV. Performance Requirements | **N/A/PASS** | Seção IV é majoritariamente sobre backend/OCR; não há orçamento de performance frontend definido além do já vigente. Esta feature não introduz nova carga de processamento. |
| Development Workflow (spec first, branch numerada, PR + review, CI gate) | **PASS** | Spec (`spec.md`) já aprovada; branch `016-frontend-architecture-refactor` segue a convenção sequencial já usada pelas 15 features anteriores (`NNN-nome`, sem prefixo `feat/` — desvio pré-existente da constituição, já presente em 100% das features anteriores, não introduzido por esta) [ver Complexity Tracking]. |
| Technology Standards (Frontend: React + Vite; TS preferido; mudanças de stack exigem emenda) | **PASS** | O stack **travado** pela constituição é apenas "React + Vite; TypeScript preferido" — permanece igual (upgrade de versão do React, não troca de framework). Router/Query/Zustand/RHF/Zod/Tailwind não são mencionados na constituição como travados; são adições, não substituições do que está travado. Nenhuma emenda constitucional é necessária. |

**Resultado**: Nenhuma violação. Nenhuma linha da Complexity Tracking table é
necessária além da nota informativa abaixo sobre a convenção de branch.

## Project Structure

### Documentation (this feature)

```text
docs/specs/016-frontend-architecture-refactor/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── module-boundaries.md   # Phase 1 output — contrato de API pública por módulo
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

Projeto web existente (`docuparse-project/backend-core` Django,
`docuparse-project/backend-ocr` FastAPI, `docuparse-project/backend-com`,
`docuparse-project/frontend` React/Vite) — **esta feature só toca
`docuparse-project/frontend`**. Estrutura alvo (de `frontend_rules.md`),
partindo do estado atual (tudo em `src/main.tsx` + `src/models/**` +
`src/types.ts`):

```text
docuparse-project/frontend/
├── src/
│   ├── app/                        # NOVO — shell: bootstrap, Router, providers (Query/Auth), ErrorBoundary raiz
│   │   ├── main.tsx                 # substitui o atual src/main.tsx (só bootstrap)
│   │   ├── router.tsx
│   │   └── providers/
│   ├── modules/                     # NOVO — um por domínio, extraído incrementalmente do monólito
│   │   ├── auth/                    # AuthContext/AuthProvider/useAuth/LoginPage/PermissionGuard
│   │   ├── documents/                # Dashboard/Inbox/Approved/Rejected/Validation/DocumentTable/useDocumentPage→useQuery
│   │   ├── operations/               # OperationsView (DLQ) → useQuery/useMutation
│   │   ├── settings/                 # SettingsView + painéis (OCR/Email/WhatsApp/Integrações/Schema/Exemplos) → RHF+Zod
│   │   ├── admin/                    # GerenciarUsuarios/GerenciarRoles
│   │   └── upload/                   # UploadView
│   ├── shared/                       # NOVO — domain-agnostic
│   │   ├── components/               # Alert/EmptyState/Field/Metric/SearchInput/StatusBadge/KeyValueGrid/Pagination/ConfirmDialog
│   │   ├── hooks/
│   │   ├── lib/                      # instâncias axios + interceptor JWT (hoje no topo de main.tsx) + queryClient
│   │   ├── types/                     # atual src/types.ts
│   │   └── utils/                     # errorMessages.ts (formaliza readError/asApiError atuais)
│   ├── models/                        # já existente — dados de schema por tipo de documento (boleto/nota_fiscal/contadeagua/recibo); inalterado por esta feature
│   └── main.tsx                       # REMOVIDO ao final da migração (Fase 7) — substituído por src/app/main.tsx
├── eslint.config.js                  # NOVO (Fase 0)
├── .prettierrc                        # NOVO (Fase 0)
├── tailwind.config.ts                 # migrado para formato v4 (Fase 1)
└── src/__tests__/                     # existente (679 linhas) — preservado e estendido por módulo
```

**Structure Decision**: Reestruturação **in-place** do único pacote
`docuparse-project/frontend` (sem novo diretório/projeto, sem monorepo) —
consistente com a arquitetura web já existente do DocuParse (3 backends +
1 frontend). A extração é incremental: durante a transição, `src/main.tsx`
(monólito original) e `src/app|modules|shared` (novo) **coexistem**; o
monólito só é removido na Fase 7 quando nada mais importa dele.

## Complexity Tracking

> Nenhuma violação da Constitution Check exige justificativa. Nota informativa
> (não é uma violação introduzida por esta feature):

| Observação | Contexto | Por que não é tratado como violação |
|---|---|---|
| Nome de branch `016-frontend-architecture-refactor` não segue o padrão `feat/###-short-description` da constituição | O tooling Spec Kit do projeto (`.specify/scripts/bash/create-new-feature.sh`) gera branches `NNN-nome` diretamente, sem prefixo `feat/` | As 15 features anteriores (`001-workflow-redesign` … `015-superlogica-discovery-spike`) já seguem esse mesmo padrão gerado pelo tooling — é uma convenção de ferramenta já estabelecida no repositório, não um desvio introduzido por esta feature. Corrigi-la (se desejado) é uma mudança de tooling/constituição independente, fora do escopo desta refatoração de frontend. |
