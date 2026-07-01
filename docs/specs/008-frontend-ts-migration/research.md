# Phase 0 — Research: Migração do Frontend para TypeScript

Decisões técnicas que resolvem o Technical Context. Complementa o documento de análise [TYPESCRIPT_MIGRATION.md](../../../docuparse-project/frontend/TYPESCRIPT_MIGRATION.md). Nenhum `NEEDS CLARIFICATION` remanescente (Q1/Q2 resolvidas no `/speckit-clarify`).

## D1 — Estratégia de conversão: rename in-place + tipagem incremental

**Decision**: Estratégia A (conversão direta) — `git mv` de `.jsx`→`.tsx` e `.js`→`.ts`, com `tsconfig` permissivo no início (`allowJs: true`, `strict: false`) e endurecimento por etapas. Sem dividir o monólito.

**Rationale**: É a única coerente com FR-004 (preservar estrutura) e com a meta de zero mudança funcional. `git mv` preserva histórico. O modo permissivo evita um "big bang" de erros ao renomear o arquivo de 4047 linhas.

**Alternatives considered**:
- *Criação paralela (Estratégia B)*: duplicar um arquivo de 4047 linhas é inviável e perigoso. Rejeitada.
- *Migração por módulos/domínio (Estratégia C)*: exigiria quebrar o monólito antes — refatoração estrutural proibida por FR-004. Rejeitada (trabalho futuro).

## D2 — Versão e configuração do TypeScript

**Decision**: `typescript` ~5.4 (compatível com Vite 5 / React 18). `tsconfig.json` com `jsx: "react-jsx"`, `moduleResolution: "bundler"`, `noEmit: true`, `allowJs: true` inicialmente, `paths` espelhando o alias `@ → ./src`. `tsconfig.node.json` (composite) para `vite.config.ts`. `src/vite-env.d.ts` com `ImportMetaEnv` (há `import.meta.env.VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN`).

**Rationale**: Vite não type-checка no build — a validação é via `tsc --noEmit` (FR-006). `bundler` resolution casa com o Vite. `paths` mantém o alias atual (FR-007). `vite-env.d.ts` cobre FR-008.

**Alternatives considered**: `ts-loader`/Babel typecheck — desnecessário no ecossistema Vite. Rejeitado.

## D3 — Endurecimento gradual do `strict` (gate final)

**Decision**: Subir o rigor por etapas: `strict:false` → `noImplicitAny:true` → `strictNullChecks:true` → `strict:true`. **Gate de aceite** (clarify Q2=A): `strict: true` ativo com **zero erros bloqueantes**; `any` **pontual permitido** onde a tipagem completa for custosa, desde que **documentado** (comentário/justificativa) — sem proibição de `any` e sem exigir eliminar todos.

**Rationale**: Reduz risco de travar a entrega num monólito grande, mantendo o ganho de tipagem. Alinhado à decisão do usuário.

**Alternatives considered**: `strict` total + proibição de `any` (Q2=B) — esforço desproporcional; rejeitado pelo usuário. Não atingir strict (Q2=C) — abaixo do objetivo; rejeitado.

## D4 — Stack de testes automatizados (novo escopo — Q1=C)

**Decision**: **Vitest** (runner nativo do Vite) + **@testing-library/react** + **@testing-library/user-event** + **jsdom** (ambiente DOM) + **MSW (Mock Service Worker)** para simular os endpoints do backend. Scripts `test` e `test:run`/`coverage`. Config de teste embutida no `vite.config.ts` (bloco `test`).

**Rationale**:
- Vitest reusa a config/transform do Vite → zero duplicação e suporte nativo a TSX/aliases; menor atrito que Jest.
- Testing Library testa pela ótica do usuário (renderização, interação), ideal para **provar preservação de comportamento** sem acoplar a internals.
- **MSW** intercepta as chamadas axios no nível de rede, permitindo validar que as **integrações continuam idênticas** (mesmos endpoints/params) com respostas realistas — cobre FR-024 e SC-002 com fidelidade, sem mockar axios manualmente em cada teste.

**Alternatives considered**:
- *Jest + RTL*: exigiria configurar transform/ESM/aliases à parte do Vite. Rejeitado (atrito).
- *axios-mock-adapter*: mais simples, porém mocka no nível do cliente (menos fiel às integrações reais). MSW preferido; pode ser fallback pontual.
- *Playwright/Cypress (E2E)*: cobertura ótima de fluxo, mas exige stack de runtime/CI mais pesada e o backend rodando. Fica como **opcional/futuro**; o gate desta entrega é testes de componente/integração com MSW.

## D5 — Escopo e meta de cobertura dos testes

**Decision**: A suíte cobre os **fluxos principais** exigidos pela spec:
- **Telas**: render de Login, Dashboard, Inbox, Validação, Aprovados, Rejeitados, Operações, Configurações, Usuários, Roles (smoke + asserts de elementos-chave).
- **Permissões**: visibilidade de navegação e gating por `permissions` (PermissionGuard / NAV_ITEMS).
- **Integrações**: fluxos com backend mockado por MSW — login/`/me`, listagem de documentos, extração, **salvar campos** (versão/conflito 409), **histórico de versões**, aprovar/rejeitar, configurações.
Meta de cobertura: **fluxos críticos ≥ 90%** (validação/permissões/auth), **demais fluxos ≥ 80%** das ramificações exercitadas; a métrica é aplicada às **funções/fluxos cobertos**, não exigida sobre 100% das 4047 linhas de uma vez (pragmatismo alinhado ao objetivo de migração).

**Rationale**: Equilibra a exigência de regressão automatizada (Q1=C) com o esforço viável num monólito sem seams de teste. Prioriza o que protege o usuário e os contratos de API.

**Alternatives considered**: Exigir 80% de linha sobre o arquivo inteiro imediatamente — esforço desproporcional e frágil; adiado para evolução incremental.

## D6 — Tipagem dos dados (DTOs) espelhando o backend

**Decision**: Definir tipos em `src/types.ts` (ou topo de `main.tsx`) espelhando os serializers reais do `backend-core` (`documents/serializers.py`), incluindo `active_field_version_number` e `ExtractionFieldVersion` (feature 007) e o **formato duplo** de campo (`ExtractionField | string`) tratado por `parseFieldEntry` como type guard.

**Rationale**: Garante fidelidade aos contratos sem alterá-los (FR-017). Detalhes em [data-model.md](data-model.md).

**Alternatives considered**: Gerar tipos a partir de OpenAPI — o backend não expõe schema OpenAPI consolidado; geração automática fora de escopo. Tipagem manual fiel aos serializers é suficiente.

## D7 — Compatibilidade Docker/dev

**Decision**: Garantir `typescript` e libs de teste em `devDependencies` **antes** do `npm install` da imagem; manter `.dockerignore` (criado) para não copiar `node_modules` do host. `npm run dev`/Vite servem `.tsx` nativamente — sem mudança no Dockerfile/compose.

**Rationale**: Evita reincidência do incidente de boot do Vite (node_modules do host). Cobre FR-021.

**Alternatives considered**: Nenhuma — é higiene necessária.
