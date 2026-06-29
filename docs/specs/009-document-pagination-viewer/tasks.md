---

description: "Task list for Otimização da Consulta e Navegação de Documentos"
---

# Tasks: Otimização da Consulta e Navegação de Documentos

**Input**: Design documents from `docs/specs/009-document-pagination-viewer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/documents-pagination-and-file.md, quickstart.md

**Tests**: INCLUÍDOS E OBRIGATÓRIOS — exigidos pela Constituição (II. Testing
Standards: testes unitários de handlers e teste de contrato antes da
implementação; cobertura ≥ 80%) e pelos contratos desta feature.

**Organization**: Agrupadas por user story (US1 Paginação P1, US2 Visualização
P2). Ordem de execução: Setup → Foundational → US1 → US2 → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1–US2 (apenas nas fases de story)

## Path Conventions

Web app com dois pacotes: `docuparse-project/backend-core/` (Django) e
`docuparse-project/frontend/` (React/Vite). Caminhos relativos à raiz do repo.

⚠️ **Conflitos de arquivo (sequencialidade obrigatória)**:
- `docuparse-project/frontend/src/main.tsx` (monólito) é tocado por várias tasks
  de frontend → essas tasks são **sequenciais** entre si (não `[P]`).
- `docuparse-project/backend-core/documents/views.py` é tocado pela paginação
  (US1) e pela auth do arquivo (US2) → essas duas tasks são **sequenciais**.
- Arquivos de teste distintos, `pagination.py`, `types.ts` e `handlers.ts` são
  arquivos próprios → permitem `[P]`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar ponto de partida verde antes de mudar contratos.

- [X] T001 Estabelecer baseline verde: rodar `docker compose exec backend-core python manage.py test documents` e `docker compose exec frontend npm run test:run`, registrando o estado inicial (suítes passando) antes de alterar o contrato de `GET /documents`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra compartilhada de paginação (backend) e tipos (frontend) que
habilita as stories. BLOQUEIA a US1 (a US2 é independente e pode começar após o
Setup).

**⚠️ CRITICAL**: Concluir T002/T003 antes da implementação da US1.

- [X] T002 [P] Criar helper de paginação reutilizável em `docuparse-project/backend-core/documents/pagination.py`: parse de `page` (default 1) e `page_size` (default 25, **cap 25**, reusando o estilo de `_positive_int`), cálculo de `count`/`total_pages`, recorte `queryset[offset:offset+page_size]` e builder do envelope `{results, count, page, page_size, total_pages}` (data-model.md / research D1).
- [X] T003 [P] Adicionar tipos `Paginated<T>` e `DocumentListParams` em `docuparse-project/frontend/src/types.ts` (data-model.md).

**Checkpoint**: Helper de paginação e tipos disponíveis para a US1.

---

## Phase 3: User Story 1 - Paginação das listagens (Priority: P1) 🎯 MVP

**Goal**: Listagens de documentos (Dashboard, Inbox, Aprovados, Rejeitados)
paginadas server-side (≤ 25/página), com navegação, posição e busca/filtros
sobre todo o conjunto (incluindo valores de campos extraídos), sem carregar a
base inteira no cliente.

**Independent Test**: Com base > 25 documentos, cada uma das 4 telas mostra ≤ 25
itens por página, navega entre páginas, exibe "Página X de Y" + total, e
busca/filtros retornam resultados de todo o conjunto reiniciando na página 1.

### Tests for User Story 1 ⚠️ (escrever e ver FALHAR antes de implementar)

- [X] T004 [P] [US1] Teste de contrato/integração do `GET /documents` paginado em `docuparse-project/backend-core/documents/tests/test_documents_pagination.py`: envelope `{results,count,page,page_size,total_pages}`; `page_size` respeita cap 25; navegação por `page`; `count`/`total_pages` corretos; lista vazia coerente; sem auth → 401; sem permissão → 403.
- [X] T005 [P] [US1] Teste de filtros/busca no mesmo arquivo: `status` single e CSV (buckets Inbox/Aprovados/Rejeitados); `search` por `original_filename`/`status`/`document_type`/`channel`; `search` cobrindo **valores de `extraction_result.fields`** (Clarifications); mapeamento de rótulos de status (ex.: "aprovado"→`APPROVED`).
- [X] T006 [P] [US1] Testes de frontend dos controles de paginação em `docuparse-project/frontend/src/__tests__/pagination.test.tsx` (MSW): navegação anterior/próxima, posição (página/total/contagem), reset para página 1 ao buscar/filtrar, botões desabilitados nos limites (primeira/última página).

### Implementação — Backend (US1)

- [X] T007 [US1] Implementar paginação + busca/filtros server-side em `documents_inbox_view` (`docuparse-project/backend-core/documents/views.py`) usando o helper de T002: aceitar `page`, `page_size` (cap 25), `status` (single ou CSV), `tenant` e `search`; aplicar `icontains` em nome/status/tipo/canal **e** nos valores de `extraction_result.fields` (research D2); mapear rótulos de status comuns; manter ordenação `-received_at`; remover o corte fixo `[:200]`; retornar o envelope. (depende de T002)

### Implementação — Frontend (US1) — `main.tsx` sequencial

- [X] T008 [US1] Criar componente `Pagination` em `docuparse-project/frontend/src/main.tsx` (controles anterior/próxima — e primeira/última quando aplicável —, exibição "Página X de Y" e total de registros; acessível: botões com rótulo/aria e navegação por teclado; desabilitar nos limites).
- [X] T009 [US1] Trocar o consumo global por paginado em `docuparse-project/frontend/src/main.tsx`: substituir `api.get<Document[]>('/documents')` por `api.get<Paginated<Document>>('/documents', { params })`; introduzir estado `page`/`search` por tela; resetar `page=1` ao mudar busca/filtro; preservar a página atual no auto-refresh de processamento. (depende de T003, T008)
- [X] T010 [US1] Adaptar as 4 telas no escopo em `docuparse-project/frontend/src/main.tsx` (Dashboard "Documentos", Inbox, Aprovados, Rejeitados): cada uma busca sua página com `status` (CSV por bucket) + `search` server-side, renderiza `<Pagination>`, e deixa de fatiar/filtrar localmente (remoção do uso client-side de `filterDocuments`/slice nessas telas). O seletor de documento de referência em Configurações **permanece inalterado** (fora do escopo — Clarifications). (depende de T009)
- [X] T011 [US1] Ajustar as métricas do Dashboard (Total/Pendentes/Aprovados/Falhas) em `docuparse-project/frontend/src/main.tsx` para usar contagens por bucket (via `count` do envelope por consulta de status, ou fonte de contagem dedicada) em vez do array completo (research D4). (depende de T009)
- [X] T012 [US1] Atualizar os handlers MSW para o envelope paginado em `docuparse-project/frontend/src/__tests__/mocks/handlers.ts` e ajustar os testes existentes que assumiam lista crua de `/documents` (`flows.test.tsx`, `screens.test.tsx`, `permissions.test.tsx`, `auth.test.tsx`) para o novo formato, deixando toda a suíte verde (`npm run test:run`). (depende de T007 para refletir o contrato real)

**Checkpoint**: US1 completa — 4 telas paginadas, busca/filtros server-side,
suíte verde. **MVP entregável.**

---

## Phase 4: User Story 2 - Visualização do documento original (Priority: P2)

**Goal**: A ação de visualização (olho) passa a exibir o documento original
embutido, **somado** às informações já mostradas, sem download, respeitando
permissões.

**Independent Test**: Acionar o olho de um registro mostra as informações
existentes + a pré-visualização do documento correto (PDF/imagem), sem download;
usuário sem permissão não vê o documento; fechar volta ao mesmo ponto da lista.

### Tests for User Story 2 ⚠️ (escrever e ver FALHAR antes de implementar)

- [X] T013 [P] [US2] Teste backend da autorização de `GET /documents/{id}/file` em `docuparse-project/backend-core/documents/tests/test_documents_pagination.py`: usuário com permissão → 200 + bytes corretos; usuário sem permissão → 403; token interno válido → 200; sem credenciais → 401; arquivo ausente → 404.
- [X] T014 [P] [US2] Teste de frontend do preview no modal em `docuparse-project/frontend/src/__tests__/flows.test.tsx` (MSW): ao acionar o olho, as informações já existentes permanecem e a pré-visualização (blob → object URL) é renderizada; estado de erro quando o arquivo não carrega; sem download (mockar `URL.createObjectURL`).

### Implementação (US2)

- [X] T015 [US2] Reforçar a autorização de `document_file_view` em `docuparse-project/backend-core/documents/views.py`: aceitar **JWT de usuário + `require_permission("inbox.view")`** além do token interno de serviço, mantendo o `FileResponse` (local ou externo via `document.file_uri`). (depende de T007 — mesmo arquivo `views.py`)
- [X] T016 [US2] Adicionar a seção de pré-visualização ao `EmailMetadataModal` em `docuparse-project/frontend/src/main.tsx`, **sem remover** as informações existentes (seção adicional ao lado): buscar o arquivo via `api.get('/documents/{id}/file', { responseType: 'blob' })`, gerar `URL.createObjectURL`, renderizar iframe (PDF) / `<img>` (imagem) / fallback amigável; estados de loading e erro; `URL.revokeObjectURL` no cleanup. (depende de T010 — mesmo `main.tsx`)

**Checkpoint**: US1 e US2 funcionando de forma independente.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T017 [P] Rodar `docker compose exec frontend npm run coverage` e garantir o piso de cobertura (incluindo os novos `pagination.test.tsx`/preview); confirmar cobertura dos novos handlers de backend (`manage.py test documents`).
- [X] T018 [P] Limpeza em `docuparse-project/frontend/src/main.tsx`: remover código client-side de filtragem/slice agora obsoleto e imports não usados; garantir `tsc --noEmit` limpo (strict) e terminologia "documento" consistente (Constituição I/III).
- [X] T019 Revalidar Docker (`docker compose build --no-cache frontend backend-core` + `up --force-recreate`) e executar o checklist de regressão do `quickstart.md` (paginação nas 4 telas + preview do documento), registrando evidência.
- [X] T020 [P] Atualizar documentação (quickstart e, se aplicável, README/`TYPESCRIPT_MIGRATION.md`) com o estado final (endpoint paginado, parâmetros, preview).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA a US1.
- **US1 (Phase 3)**: depende da Foundational (T002/T003).
- **US2 (Phase 4)**: depende da Foundational apenas para o tipo `Document`/infra já
  existente; pode iniciar após o Setup, mas o frontend (T016) toca `main.tsx`
  depois da US1 (T010) e o backend (T015) toca `views.py` depois da US1 (T007).
- **Polish (Phase 5)**: depende das stories desejadas concluídas.

### Conflitos de arquivo (sequencialidade)

- `frontend/src/main.tsx`: T008 → T009 → T010 → T011 → T016 → T018 (sequencial).
- `backend-core/documents/views.py`: T007 → T015 (sequencial).
- `documents/tests/test_documents_pagination.py`: T004, T005 e T013 escrevem no
  mesmo arquivo → coordenar (sequencial entre si) ou separar em arquivos.
- `handlers.ts`/`pagination.test.tsx`/`types.ts`/`pagination.py`: arquivos
  próprios → `[P]`.

### Within Each User Story

- Testes (T004–T006, T013–T014) escritos e **falhando** antes da implementação.
- Backend (helper → view) antes de integrar; Frontend: `Pagination` → consumo →
  telas → métricas.

### Parallel Opportunities

- Foundational: T002 (backend) e T003 (frontend) em paralelo.
- US1 tests: T006 (frontend) em paralelo com T004/T005 (backend); T004/T005 no
  mesmo arquivo → sequenciais entre si.
- US2 tests: T013 (backend) e T014 (frontend) em paralelo.
- Polish: T017, T020 em paralelo.

---

## Parallel Example: Foundational + US1 tests

```bash
# Foundational (arquivos distintos):
Task: "T002 pagination.py — helper de paginação (backend)"
Task: "T003 types.ts — Paginated<T> + DocumentListParams (frontend)"

# Testes da US1 (frontend em paralelo ao backend):
Task: "T006 pagination.test.tsx — controles de paginação (MSW)"
Task: "T004 test_documents_pagination.py — contrato do GET /documents paginado"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) + Phase 2 (Foundational).
2. Phase 3 (US1): paginação server-side + telas + métricas + suíte verde.
3. **PARAR e VALIDAR**: 4 telas paginadas, busca/filtros corretos, performance
   melhor, testes verdes.

### Incremental Delivery

1. Setup + Foundational → base de paginação.
2. US1 → paginação (demo — MVP de performance/navegação).
3. US2 → pré-visualização do documento original (demo).
4. Polish → cobertura, limpeza, Docker + regressão, docs.

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente.
- A mudança de `GET /documents` (lista crua → envelope) é **breaking** para o
  cliente (controlado): T012 mantém a suíte verde atualizando MSW e testes.
- **Nunca** remover informações já exibidas na ação de visualização (FR-012/019);
  apenas acrescentar a pré-visualização.
- Preservar permissões (FR-015) e ausência de download (FR-011) via blob
  autenticado.
- Commit por task ou grupo lógico; cada etapa deixa app + suíte verdes.
