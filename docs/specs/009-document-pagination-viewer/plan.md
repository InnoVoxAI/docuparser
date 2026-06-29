# Implementation Plan: Otimização da Consulta e Navegação de Documentos

**Branch**: `009-document-pagination-viewer` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/009-document-pagination-viewer/spec.md`

## Summary

Duas mudanças complementares na consulta documental:

1. **Paginação server-side** do endpoint de listagem de documentos
   (`GET /documents`), retornando no máximo 25 registros por página, com
   busca/filtros resolvidos no backend e metadados de paginação (página atual,
   total de páginas, total de registros). O frontend passa a buscar **uma página
   por vez por tela** nas 4 listagens no escopo (Dashboard, Inbox, Aprovados,
   Rejeitados — o seletor de documento de referência em Configurações fica de
   fora, ver Clarifications da spec), com controles de navegação reutilizáveis,
   deixando de carregar a base inteira e filtrar no cliente. A busca server-side
   inclui os valores dos campos extraídos (`extraction_result.fields`),
   preservando o comportamento atual.

2. **Pré-visualização do documento original** embutida na ação de visualização
   (ícone de olho) das listagens. A pré-visualização é **adicionada** ao modal de
   informações já existente (`EmailMetadataModal`), sem remover nada, buscando o
   arquivo via `GET /documents/{id}/file` como *blob autenticado* (carrega o JWT
   do usuário), renderizado inline (PDF/imagem) sem download e respeitando as
   permissões do usuário.

Abordagem técnica: estender o backend Django/DRF com paginação + busca no
queryset e reforçar a autorização do endpoint de arquivo para aceitar o JWT do
usuário (mantendo o token interno para serviços); estender o frontend
React/TS com um hook/controle de paginação e a seção de preview no modal.

## Technical Context

**Language/Version**: Backend — Python 3.10 + Django + Django REST Framework
(constituição pede 3.11+; ambiente atual é 3.10 — sem mudança nesta feature).
Frontend — TypeScript 5.4 + React 18 + Vite 5 (modo `strict`).

**Primary Dependencies**: DRF, `rest_framework_simplejwt` (auth JWT),
`docuparse_storage.LocalStorage` (arquivo); Frontend: `axios`, `lucide-react`;
testes: Vitest + Testing Library + MSW (frontend), Django test/pytest (backend).

**Storage**: PostgreSQL (metadados de documentos). Arquivo original via
`docuparse_storage.LocalStorage` (filesystem local; MinIO existe no compose mas o
serving atual é local — a feature acessa o arquivo **através do endpoint**, que
abstrai o backing store).

**Testing**: Django tests para o endpoint de listagem paginado e para a
autorização do endpoint de arquivo; Vitest + MSW para os controles de paginação
e o preview no modal.

**Target Platform**: Contêineres Linux (Docker Compose); navegador (320–1920px).

**Project Type**: Web application — `docuparse-project/backend-core/` (Django) +
`docuparse-project/frontend/` (React/Vite).

**Performance Goals**: Listagem (endpoint não-processante) < 200 ms p95
(Constituição IV); payload de cada página ≤ 25 registros; redução ≥ 50% no tempo
até a lista ficar utilizável com base grande (SC-002).

**Constraints**: Preservar 100% do comportamento e das informações já exibidas
(FR-018/FR-019); não carregar a base completa no cliente (FR-007); respeitar as
permissões existentes (FR-015); sem download na visualização (FR-011).

**Scale/Scope**: 5 telas/listagens de documentos no frontend; 1 endpoint de
listagem + 1 endpoint de arquivo no backend; base documental em crescimento
contínuo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality** — ⚠️ Parcial. `frontend/src/main.tsx` já excede 400 linhas
  (violação **pré-existente**, herdada da migração 008; não é introduzida aqui).
  Mitigação: o novo código de paginação/preview entra como funções/componentes
  pequenos e coesos; sem aumentar a dívida estrutural. Backend mantém type hints
  e funções curtas. Sem dead code; imports limpos.
- **II. Testing Standards** — ✅. Testes unitários para o handler de listagem
  paginada (página, page_size, busca, filtros, limites) e para a autorização do
  endpoint de arquivo (usuário com/sem permissão; token interno). Frontend:
  testes dos controles de paginação (navegação, posição, reset ao filtrar) e do
  preview no modal (render PDF/imagem, sem download, permissão). Meta ≥ 80%.
- **III. UX Consistency** — ⚠️ Parcial (envelope). A Constituição pede
  `{data,error,meta}`, mas os endpoints atuais retornam respostas cruas e a
  feature 007 já usa `{results, count, ...}`. Para **consistência interna** e
  evitar um envelope "meio migrado", a paginação reusa/estende o padrão
  `{results, count, page, page_size, total_pages}` (ver Complexity Tracking).
  Demais itens de UX são atendidos: estados de loading/erro nos controles e no
  preview; navegação acessível (botões com rótulos/aria, teclado); responsivo;
  terminologia "documento" consistente.
- **IV. Performance** — ✅. A paginação reduz payload e tempo de resposta da
  listagem (alvo < 200 ms p95). Busca/filtros e contagem executados no banco com
  índices existentes (`received_at`, `status`).

**Resultado do gate**: PASS com 2 desvios documentados e justificados
(main.tsx pré-existente; envelope de paginação por consistência interna).

## Project Structure

### Documentation (this feature)

```text
docs/specs/009-document-pagination-viewer/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 (/speckit-plan)
├── data-model.md        # Phase 1 (/speckit-plan)
├── quickstart.md        # Phase 1 (/speckit-plan)
├── contracts/           # Phase 1 (/speckit-plan)
│   └── documents-pagination-and-file.md
├── checklists/
│   └── requirements.md  # criado pelo /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/backend-core/
├── documents/
│   ├── views.py                 # documents_inbox_view → paginação + busca;
│   │                            # document_file_view → auth de usuário + permissão
│   ├── serializers.py           # DocumentListSerializer (reuso)
│   ├── pagination.py            # (novo) helper de paginação reutilizável
│   └── tests/
│       ├── test_api.py          # estender: paginação/busca/limites
│       └── test_documents_pagination.py  # (novo) casos de paginação + file auth
└── core/settings.py             # (se necessário) ajuste de auth do file endpoint

docuparse-project/frontend/
├── src/
│   ├── main.tsx                 # telas de listagem → consumo paginado;
│   │                            # EmailMetadataModal → seção de preview
│   ├── types.ts                 # Paginated<T>, parâmetros de listagem
│   └── __tests__/
│       ├── pagination.test.tsx  # (novo) controles + navegação + reset
│       └── flows.test.tsx       # estender: preview do documento no modal
└── vitest.config.ts
```

**Structure Decision**: Web application com os dois pacotes existentes
(`backend-core` Django + `frontend` React/Vite). A feature toca apenas o app
`documents` no backend e `main.tsx`/`types.ts` no frontend, reusando os padrões
estabelecidos (FBV `@api_view`, helper `_positive_int`, suíte Vitest+MSW).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Resposta de paginação `{results, count, page, page_size, total_pages}` em vez do envelope `{data, error, meta}` da Constituição III | Consistência interna: a feature 007 (`field-versions`) já estabeleceu `{results, count, ...}`; os demais endpoints retornam respostas cruas. Migrar só este endpoint para `{data,error,meta}` criaria um envelope "meio migrado" e exigiria adaptação assimétrica no frontend. | Adotar o envelope completo agora obrigaria migrar **todos** os endpoints e o cliente inteiro (esforço transversal fora do escopo desta feature). Recomenda-se uma feature dedicada de padronização de envelope. |
| `main.tsx` permanece > 400 linhas (Code Quality I) | Violação pré-existente da migração 008; a regra do projeto (US1 da 008) é **não** dividir o monólito nesta etapa. | Quebrar o monólito agora misturaria refatoração estrutural com a entrega desta feature, aumentando risco de regressão. Fica como trabalho futuro já registrado. |
