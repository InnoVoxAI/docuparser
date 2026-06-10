# Tasks: Workflow and Permissions Improvements

**Input**: Design documents from `docs/specs/004-workflow-perms-improvements/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Organization**: Tasks organizadas por user story (US1–US6) conforme prioridades do spec.md. Sem testes automatizados de frontend — apenas backend quando relevante.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências pendentes)
- **[Story]**: A qual user story pertence (US1 a US6)

---

## Phase 1: Setup

**Purpose**: Verificação do estado inicial — sem criação de infraestrutura nova.

- [X] T001 Confirmar estado atual do branch `004-workflow-perms-improvements` e que todos os arquivos de spec estão em `docs/specs/004-workflow-perms-improvements/`

---

## Phase 2: Foundational (Pré-requisito Compartilhado para US1 e US2)

**Purpose**: Campos de serializer compartilhados por US1 (modal de rejeição) e US2 (colunas de data). Deve estar completo antes das duas user stories.

**⚠️ CRITICAL**: US1 e US2 dependem dos campos `approved_at` e `rejected_at` adicionados aqui.

- [X] T002 Adicionar campos `approved_at` e `rejected_at` como `SerializerMethodField` em `DocumentListSerializer` em `docuparse-project/backend-core/documents/serializers.py` — `get_approved_at` filtra `_prefetched_decisions` por `decision='approved'` e retorna `created_at.isoformat()`; `get_rejected_at` filtra por `decision='rejected'`; manter campo `decision_date` existente
- [X] T003 Adicionar setting `DOCUPARSE_AUTO_PROCESS_EXTRACTION` em `docuparse-project/backend-core/core/settings.py` — `os.environ.get('DOCUPARSE_AUTO_PROCESS_EXTRACTION', 'true').strip().lower() not in {'0', 'false', 'no'}`

**Checkpoint**: Serializer retorna `approved_at`/`rejected_at` como campos independentes; setting de extração existe.

---

## Phase 3: User Story 1 — Detalhes e Ações em Documentos Rejeitados (Priority: P1) 🎯 MVP

**Goal**: Clicar em documento REJEITADO no Dashboard abre popup dinâmico com motivo da rejeição, data/hora, botão Reprocessar e botão Excluir.

**Independent Test**: Rejeitar um documento com motivo, abrir Dashboard, clicar no documento → popup exibe motivo correto, data e as duas ações. Clicar Reprocessar → documento some do popup e status muda para RECEIVED.

### Implementation for User Story 1

- [X] T004 [US1] Criar componente `RejectedDocumentModal` em `docuparse-project/frontend/src/main.jsx` — overlay `fixed inset-0 bg-black/40 flex items-center justify-center z-50`, card central com nome do arquivo, motivo (`doc.rejection_notes || 'Motivo não informado'`), data formatada via `formatDate(doc.rejected_at ?? doc.decision_date)`, botão "Reprocessar" (chama `onReprocess(doc.id)` e fecha modal), botão "Excluir" (chama `onDelete(doc.id)` e fecha modal), botão "Fechar" com ícone X
- [X] T005 [US1] Adicionar estado `rejectedModal` (null ou objeto do documento) no componente `App` em `docuparse-project/frontend/src/main.jsx` e passar handlers `onSelectRejected`, `onReprocess`, `onDelete` para o componente `Dashboard`
- [X] T006 [US1] Atualizar componente `Dashboard` em `docuparse-project/frontend/src/main.jsx` para aceitar props `onSelectRejected`, `onReprocess`, `onDelete` e, na `DocumentTable`, tornar linhas de documentos com `status === 'REJECTED'` clicáveis chamando `onSelectRejected(doc)` — substituir `onSelectDocument={() => {}}` por lógica condicional
- [X] T007 [US1] Renderizar `<RejectedDocumentModal>` no `App` quando `rejectedModal !== null`, passando o documento e os handlers de fechar/reprocessar/excluir em `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: Clicar em documento REJECTED no Dashboard abre modal com motivo, data e ações funcionais.

---

## Phase 4: User Story 2 — Datas de Aprovação e Rejeição no Dashboard (Priority: P2)

**Goal**: Dashboard exibe colunas separadas "Aprovado em" e "Rejeitado em" por documento; tela Aprovados usa `approved_at`.

**Independent Test**: Aprovar um documento e um rejeitado → Dashboard mostra datas corretas em colunas distintas. Documentos sem decisão → colunas ficam vazias sem erro.

### Implementation for User Story 2

- [X] T008 [P] [US2] Atualizar `ApprovedView` em `docuparse-project/frontend/src/main.jsx` — coluna "Data de aprovação" passa a usar `doc.approved_at ?? doc.decision_date ?? doc.updated_at` em vez de `doc.decision_date ?? doc.updated_at`
- [X] T009 [P] [US2] Atualizar `DocumentTable` (usada pelo `Dashboard`) em `docuparse-project/frontend/src/main.jsx` — adicionar coluna "Decisão em" que exibe `formatDate(doc.approved_at)` quando status `APPROVED`, `formatDate(doc.rejected_at)` quando `REJECTED`, e célula vazia para outros status (nunca exibir `null` ou `undefined` como texto)

**Checkpoint**: Tabela do Dashboard exibe datas de aprovação e rejeição por documento; tela Aprovados usa campo correto.

---

## Phase 5: User Story 3 — Extração Automática após OCR (Priority: P3)

**Goal**: Após OCR concluir com sucesso, sistema inicia automaticamente extração de campos sem intervenção humana, transitando o documento para VALIDATION_PENDING.

**Independent Test**: Fazer upload de documento cujo layout tenha um `LayoutConfig` ativo → sem nenhuma ação adicional, documento chega ao status `VALIDATION_PENDING` automaticamente.

### Implementation for User Story 3

- [X] T010 [US3] Implementar função `auto_extract_after_ocr(document: Document) -> None` em `docuparse-project/backend-core/documents/services/ocr_processor.py` — checar `settings.DOCUPARSE_AUTO_PROCESS_EXTRACTION`; buscar `LayoutConfig.objects.filter(tenant=document.tenant, layout=document.layout, is_active=True).select_related('schema_config').first()`; se não encontrar layout_cfg ou `document.raw_text_uri` estiver vazio, retornar silenciosamente; ler JSON do storage via `LocalStorage`; chamar `LangExtractClient().extract_with_schema()`; salvar com `ExtractionResult.objects.update_or_create()`; chamar `document.transition_to(Document.Status.VALIDATION_PENDING)`; envolver tudo em try/except com `logger.warning`
- [X] T011 [US3] Chamar `auto_extract_after_ocr(document)` ao final de `process_document_ocr()` em `docuparse-project/backend-core/documents/services/ocr_processor.py` — adicionar chamada após `document.save()` e antes do `return document`; importar dependências necessárias (`LayoutConfig`, `LangExtractClient`, `ExtractionResult`, `LocalStorage`, `json`)

**Checkpoint**: Upload de documento com layout conhecido → status chega a `VALIDATION_PENDING` sem clique manual. Documento sem LayoutConfig configurado → fica em `OCR_COMPLETED` sem erro.

---

## Phase 6: User Story 4 — Processamento em Fila (Priority: P4)

**Goal**: Múltiplos documentos enviados simultaneamente entram em fila controlada; falhas individuais não bloqueiam os demais.

**Independent Test**: Enviar 5 documentos ao mesmo tempo → todos são processados (ou falham individualmente) sem que um bloqueie os outros. Nenhum erro 500 na API de upload.

### Implementation for User Story 4

- [X] T012 [US4] Criar arquivo `docuparse-project/backend-core/documents/services/processing_queue.py` com `ThreadPoolExecutor` global — `_MAX_WORKERS = int(os.environ.get('DOCUPARSE_PROCESSING_WORKERS', '2'))`; `_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS)`; função `submit_document_processing(document_id: int) -> None` que chama `_executor.submit(_run_processing_safely, document_id)`; função `_run_processing_safely(document_id)` que chama `process_document_ocr(document_id)` em try/except com `logger.warning`; usar `from __future__ import annotations` e type hints
- [X] T013 [US4] Atualizar `document_received_event_view` em `docuparse-project/backend-core/documents/views.py` — substituir `start_document_ocr_thread(document.id)` por `submit_document_processing(document.id)`; adicionar import de `from documents.services.processing_queue import submit_document_processing`

**Checkpoint**: Enviar vários documentos em rápida sucessão → todos entram na fila e são processados de forma ordenada. Cada falha individual gera warning no log sem interromper os demais.

---

## Phase 7: User Story 5 — Restrição da Tela Operações (Priority: P5)

**Goal**: Confirmar que a tela Operações está restrita a usuários com `operations.access`. (Já implementado — fase de verificação.)

**Independent Test**: Logar com usuário sem `operations.access` → menu "Operações" não aparece. Logar com usuário com `operations.access` → aparece.

### Implementation for User Story 5

- [X] T014 [US5] Verificar em `docuparse-project/frontend/src/main.jsx` que `NAV_ITEMS` contém `{ id: 'operations', permission: 'operations.access' }` (linha ~48) e que a view de Operações está envolvida por `<PermissionGuard code="operations.access">` (linha ~519) — se qualquer um estiver ausente, adicionar; registrar confirmação como comentário inline no spec.md se tudo estiver correto
- [X] T015 [US5] Verificar que o management command `seed_permissions` em `docuparse-project/backend-core/` inclui `operations.access` na lista de permissões criadas — se ausente, adicionar entrada ao comando

**Checkpoint**: Usuário sem `operations.access` não vê nem consegue acessar a tela Operações.

---

## Phase 8: User Story 6 — Nomes Legíveis para Permissões (Priority: P6)

**Goal**: Administrador vê descrições legíveis das permissões na tela de Roles (ex: "Upload de documentos" em vez de `documents.send`).

**Independent Test**: Abrir tela de Roles como admin → tabela mostra descrições legíveis, não códigos técnicos. Criar nova role → checkboxes exibem descrições (já funciona hoje).

### Implementation for User Story 6

- [X] T016 [P] [US6] Atualizar `RoleListSerializer.get_permissions` em `docuparse-project/backend-core/users/serializers.py` — retornar `list(obj.permissions.values('code', 'description'))` em vez de `list(obj.permissions.values_list('code', flat=True))`
- [X] T017 [P] [US6] Atualizar tabela de roles em `GerenciarRoles` em `docuparse-project/frontend/src/main.jsx` — na linha da tabela que exibe `(r.permissions || []).join(', ')`, mudar para `(r.permissions || []).map(p => p.description || p.code || p).join(', ')` para suportar tanto o formato novo (objetos) quanto legado (strings)

**Checkpoint**: Tabela de Roles mostra "Upload de documentos, Aprovar ou rejeitar documentos, ..." em vez de "documents.send, documents.validate, ...".

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validação final e consistência entre as histórias.

- [X] T018 Executar suite de testes backend existente com `cd docuparse-project/backend-core && python -m pytest` ou `python manage.py test` para confirmar zero regressões
- [X] T019 Verificar que `DocumentListSerializer` retorna os 6 campos (`id`, `status`, `rejection_notes`, `decision_date`, `approved_at`, `rejected_at`) via `docker compose exec backend-core python manage.py shell` e inspecionar output do serializer com um documento de teste

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — iniciar imediatamente
- **Foundational (Phase 2)**: Sem dependências — pode iniciar após Phase 1
- **US1 (Phase 3)**: Depende de Phase 2 (campos `approved_at`/`rejected_at` no serializer)
- **US2 (Phase 4)**: Depende de Phase 2 (mesmos campos)
- **US3 (Phase 5)**: Independente — depende apenas do Phase 2 (T003 para setting)
- **US4 (Phase 6)**: Depende de US3 — a fila chama `process_document_ocr` que inclui auto-extração
- **US5 (Phase 7)**: Totalmente independente — apenas verificação
- **US6 (Phase 8)**: Totalmente independente — backend e frontend diferentes dos demais
- **Polish (Phase 9)**: Depende de todas as fases anteriores

### User Story Dependencies

- **US1 (P1)**: Depende de Phase 2 (T002) — nenhuma dependência de outras US
- **US2 (P2)**: Depende de Phase 2 (T002) — nenhuma dependência de outras US
- **US3 (P3)**: Depende de Phase 2 (T003) — nenhuma dependência de outras US
- **US4 (P4)**: Depende de US3 completo — a fila executa `process_document_ocr` com extração integrada
- **US5 (P5)**: Sem dependências — verificação isolada
- **US6 (P6)**: Sem dependências — backend (`users/serializers.py`) e frontend (roles table) independentes

### Parallel Opportunities

- T002 (serializer) e T003 (settings) podem rodar em paralelo (arquivos diferentes)
- T004 a T007 (US1 frontend) são sequenciais — cada um depende do anterior
- T008 e T009 (US2 frontend) podem rodar em paralelo entre si
- T016 (backend US6) e T017 (frontend US6) podem rodar em paralelo
- US3 e US6 podem ser implementadas em paralelo por desenvolvedores diferentes

---

## Parallel Example: Phase 2 (Foundational)

```
# Rodar em paralelo:
Task T002: "Adicionar approved_at/rejected_at em documents/serializers.py"
Task T003: "Adicionar DOCUPARSE_AUTO_PROCESS_EXTRACTION em core/settings.py"
```

## Parallel Example: User Story 2

```
# Rodar em paralelo (arquivos não conflitam):
Task T008: "Atualizar ApprovedView — coluna Data de aprovação"
Task T009: "Atualizar DocumentTable — coluna Decisão em"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 — alto impacto operacional imediato)

1. Completar Phase 1 (Setup) + Phase 2 (Foundational)
2. Completar Phase 3 (US1: modal de rejeição) → **PARAR e VALIDAR**
3. Completar Phase 4 (US2: colunas de data) → DEMO opcional
4. Avançar para US3–US6 na sequência

### Incremental Delivery

1. Phase 2 → serializer ready (base para US1 e US2)
2. US1 → operadores vêem popup de rejeição com ações → **MVP operacional**
3. US2 → datas de aprovação/rejeição visíveis → melhora rastreabilidade
4. US3 → extração automática → elimina passo manual no workflow
5. US4 → fila de processamento → escalabilidade para múltiplos docs
6. US5 → verificação de segurança (provavelmente já OK)
7. US6 → permissões legíveis → melhora UX de admin

### Sequência Recomendada para Desenvolvedor Único

```
T001 → T002+T003 (paralelo) → T004 → T005 → T006 → T007
  → T008+T009 (paralelo)
  → T010 → T011
  → T012 → T013
  → T014+T015 (paralelo)
  → T016+T017 (paralelo)
  → T018 → T019
```

---

## Notes

- Todas as mudanças são em arquivos existentes — sem novo projeto ou framework
- `main.jsx` é o único arquivo de frontend — todas as mudanças de UI ocorrem nele
- US5 provavelmente não requer nenhuma linha nova de código
- US3 e US4 são as mais críticas para estabilidade — testar com cuidado
- Commit sugerido após cada Phase completa
