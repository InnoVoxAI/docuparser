# Implementation Plan: Migração do Frontend DocuParse de JavaScript/JSX para TypeScript/TSX

**Branch**: `008-frontend-ts-migration` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/008-frontend-ts-migration/spec.md`

> Companion técnico detalhado já existente: [docuparse-project/frontend/TYPESCRIPT_MIGRATION.md](../../../docuparse-project/frontend/TYPESCRIPT_MIGRATION.md) (inventário completo + estratégia). Este plano consolida as decisões e incorpora o novo escopo de **suíte de testes automatizada** (clarify Q1=C).

## Summary

Migrar o frontend (React 18 + Vite 5, JS/JSX) para TypeScript/TSX **preservando 100% do comportamento, visual e integrações**, sem refatoração estrutural. Abordagem: habilitar TypeScript em modo permissivo (`allowJs`), renomear `src/models/**/*.js` → `.ts` e `src/main.jsx` → `main.tsx` via `git mv`, tipar incrementalmente (núcleo Auth/axios → componentes → DTOs de domínio) e endurecer `tsconfig` por etapas até `strict: true` com zero erros bloqueantes (`any` pontual documentado permitido). Adicionalmente, introduzir uma **suíte de testes automatizada** (Vitest + Testing Library + jsdom + MSW) cobrindo as telas, as integrações com o backend e as regras de permissão, executável por comando e integrada ao build, como rede de segurança de regressão.

## Technical Context

**Language/Version**: TypeScript ~5.4 (alvo) sobre o código JS/JSX atual; JSX/TSX via React 18

**Primary Dependencies**: React 18, Vite 5, `@vitejs/plugin-react`, Tailwind 3, axios, lucide-react, clsx, tailwind-merge (todas já com tipos próprios; `@types/react`/`@types/react-dom` já presentes)

**Storage**: N/A (frontend; estado em memória via `useState`/Context; sessão em `localStorage`)

**Testing**: Vitest + `@testing-library/react` + `@testing-library/user-event` + jsdom; mock de rede com MSW (Mock Service Worker). Comando `npm run test`; checagem de tipos `npm run typecheck` (`tsc --noEmit`)

**Target Platform**: Navegador moderno (SPA servida por Vite; containerizada via Docker `node:18-alpine`)

**Project Type**: Web SPA (single package em `docuparse-project/frontend/`)

**Performance Goals**: Sem regressão perceptível vs. estado atual; tempo de boot do dev server e tamanho de bundle equivalentes (TS é apagado em build — overhead nulo em runtime)

**Constraints**: Preservar layout/UX/navegação/permissões/contratos de API (FR-016–FR-019); **não** quebrar o monólito nem reorganizar a arquitetura (FR-004); não introduzir libs de estado/roteamento/dados (FR-019; testes são permitidos); coexistência JS/TS durante a transição (FR-009); `strict` ao final com `any` pontual documentado (FR-010)

**Scale/Scope**: 1 arquivo monolítico `src/main.jsx` (~4047 linhas, ~60 componentes, 1 context, 1 hook, 3 instâncias axios, ~43 chamadas) + 15 arquivos de dados em `src/models/**` (~3300 linhas) + `index.css`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|-----------|-----------|--------|
| I. Code Quality | A migração **avança** a tipagem (type hints/TS). Lint sem ESLint configurado hoje (não é requisito). **Tensão**: a regra "arquivos ≤ 400 linhas" conflita com `main.tsx` (~4047), mas FR-004 proíbe explicitamente quebrar o monólito → ver Complexity Tracking. | PASS c/ desvio justificado |
| II. Testing Standards | Spec passa a exigir suíte automatizada (FR-024/FR-025). Plano adota Vitest+Testing Library+MSW cobrindo telas/integrações/permissões. Cobertura: alvo pragmático nos fluxos principais (ver research D5); o piso de 80%/90% da constituição é mirado nos fluxos críticos, não no monólito inteiro de uma vez. | PASS |
| III. UX Consistency | Objetivo central é **preservar** UX, layout, terminologia e estados (loading/erro). Nenhuma mudança de envelope/labels. | PASS |
| IV. Performance | TS não adiciona runtime; bundle equivalente. Sem novas chamadas. | PASS |
| Technology Standards | "Frontend: React + Vite; TypeScript preferido sobre JS" — migração **cumpre** diretamente a diretriz. Sem novas engines/serviços. | PASS |

**Resultado**: PASS com 1 desvio justificado (tamanho do arquivo) registrado em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
docs/specs/008-frontend-ts-migration/
├── plan.md              # Este arquivo
├── research.md          # Phase 0 — decisões (TS, test stack, MSW, strict gradual)
├── data-model.md        # Phase 1 — tipos de domínio e DTOs
├── quickstart.md        # Phase 1 — setup, comandos, validação
├── contracts/
│   └── frontend-types-and-test-surface.md   # "contrato": DTOs ↔ backend + superfície de testes
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (não criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/frontend/
├── package.json                 # + typescript, vitest, @testing-library/*, jsdom, msw; scripts typecheck/test
├── tsconfig.json                # NOVO — permissivo → estrito (incremental)
├── tsconfig.node.json           # NOVO — ambiente de build (vite.config)
├── vite.config.ts               # (renomeado de .js) — proxy/alias + config Vitest
├── index.html                   # ajustar src para /src/main.tsx
└── src/
    ├── vite-env.d.ts            # NOVO — ImportMetaEnv (VITE_*)
    ├── types.ts                 # NOVO (opcional) — DTOs/domínio centralizados
    ├── main.tsx                 # (renomeado de main.jsx) — tipado incrementalmente
    ├── models/**/*.ts           # (renomeados de .js) — schemas/prompts/rules/examples
    ├── index.css                # inalterado
    └── __tests__/               # NOVO — suíte Vitest (telas, integrações, permissões)
        └── mocks/               # handlers MSW espelhando endpoints existentes
```

**Structure Decision**: SPA de pacote único em `docuparse-project/frontend/`. A migração é **in-place** (rename + tipagem), preservando a estrutura atual (FR-004). A única adição estrutural permitida é a pasta de testes (`src/__tests__/`) e arquivos de configuração de TS/Vitest — nada que reorganize o código de aplicação.

## Complexity Tracking

> Desvio de constituição que precisa de justificativa.

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|----------|----------------------|-------------------------------------------|
| `src/main.tsx` excede o limite de 400 linhas/arquivo (Princípio I) | FR-004 proíbe explicitamente quebrar o monólito nesta entrega; o objetivo é **migração de tipos sem refatoração estrutural**, isolando risco | Dividir o arquivo agora misturaria refatoração estrutural com migração de tipos, multiplicando o risco de regressão visual/funcional — contraria o objetivo central (US1). Split fica como trabalho **futuro separado**, após o TS estável |
