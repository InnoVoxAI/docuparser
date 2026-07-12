# Tasks: Ajustes de Interface e Gerenciamento de Modelos de Extração

**Input**: Design documents from `docs/specs/006-ui-model-management/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [data-model.md](data-model.md) · [contracts/delete-schema-config.md](contracts/delete-schema-config.md) · [research.md](research.md)

**Tests**: Não solicitados — nenhuma tarefa de teste incluída.

**Organization**: Tarefas agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Descrição`

- **[P]**: Pode rodar em paralelo (arquivos diferentes ou seções distantes sem sobreposição)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3)
- Paths exatos incluídos em todas as descrições

---

## Phase 1: Setup

**Purpose**: Garantir baseline funcional antes das mudanças

- [X] T001 Verificar que o build do frontend passa sem erros em `docuparse-project/frontend/` executando `npm run build`

---

## Phase 2: User Story 1 — Tela de Validação Simplificada (Priority: P1) 🎯 MVP

**Goal**: Remover ruído visual na tela de validação — ocultar "Revisão da qualidade do OCR" e simplificar "Modelo Ativo" para exibir apenas o tipo.

**Independent Test**: Abrir qualquer documento em Validação → Extração → Documento e confirmar que (a) a seção "Revisão da qualidade do OCR" não aparece, e (b) a subsection "Modelo Ativo" exibe somente o campo "Tipo".

### Implementação US1

- [X] T002 [P] [US1] Remover o bloco `<section>` completo contendo "Revisao da qualidade do OCR" de `ReferenceDocumentPanel` em `docuparse-project/frontend/src/main.jsx` (~linhas 3042-3076) — manter estados `referenceReview` e `onReviewChange` intactos
- [X] T003 [P] [US1] Simplificar `ActiveTemplateHeader` removendo as pills de schema, layout e status e mantendo apenas a pill "tipo" em `docuparse-project/frontend/src/main.jsx` (~linhas 2961-2964)

**Checkpoint**: US1 completa e testável independentemente — nenhuma dependência com US2 ou US3.

---

## Phase 3: User Story 2 — Configurações de Modelo Simplificadas (Priority: P2)

**Goal**: Limpar a tela de configuração de modelos — ocultar campos técnicos internos, atualizar rótulos e remover seções desnecessárias.

**Independent Test**: Acessar Configurações → Extração → Modelo e confirmar: campos Tenant/Versão/Status ausentes; rótulos "Schema (Campos)", "Modelos existentes", "Exemplos (Few-shots anotados)" corretos; seção "Layouts existentes" e subsection "Checklist LangExtract" ocultos; versão ausente na listagem de modelos.

### Implementação US2

- [X] T004 [US2] Remover os três `<Field>` de Tenant (~linha 2407), Versao (~linha 2410) e Status (~linha 2430) do bloco `activeTab === 'setup'` em `docuparse-project/frontend/src/main.jsx` — manter os valores no `schemaForm` state para envio ao backend
- [X] T005 [US2] Renomear `<Field label="Schema">` para `<Field label="Schema (Campos)">` em `docuparse-project/frontend/src/main.jsx` (~linha 2404)
- [X] T006 [US2] Remover `<HintPanel title="Checklist LangExtract" ...>` completo e simplificar o wrapper de grid lateral (`grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]`) caso o HintPanel seja o único conteúdo da segunda coluna em `docuparse-project/frontend/src/main.jsx` (~linhas 2433-2442)
- [X] T007 [US2] Remover `<ConfigList title="Layouts existentes" ...>` e o `<div className="grid ...">` wrapper se sobrar apenas um filho em `docuparse-project/frontend/src/main.jsx` (~linha 2444)
- [X] T008 [P] [US2] Renomear string "Few-shot anotados" → "Exemplos (Few-shots anotados)" dentro de `ExamplesEditor` em `docuparse-project/frontend/src/main.jsx` (~linha 3166)

**Checkpoint**: US2 completa e testável independentemente — nenhuma dependência com US3.

---

## Phase 4: User Story 3 — Exclusão de Modelos de Extração (Priority: P3)

**Goal**: Implementar botão "Excluir" por modelo com modal de confirmação, proteção de modelos padrão e endpoint DELETE no backend.

**Independent Test**: Criar modelo de teste, clicar Excluir, confirmar → modelo desaparece. Tentar excluir `nota_fiscal_default` → ação bloqueada com mensagem. Tentar excluir modelo com layouts vinculados → mensagem de conflito exibida.

### Implementação US3 — Backend

- [X] T009 [P] [US3] Adicionar `"DELETE"` ao decorator `@api_view` e implementar handler DELETE com constante `PROTECTED_SCHEMA_IDS`, verificação de proteção (HTTP 403) e captura de `ProtectedError` (HTTP 409) em `schema_config_detail_view` em `docuparse-project/backend-core/documents/views.py` (~linha 389) — seguir o padrão de `document_delete_view` (~linha 205)

### Implementação US3 — Frontend

- [X] T010 [P] [US3] Adicionar constante `PROTECTED_SCHEMA_IDS` e criar componente `SchemaList` (seção "Modelos existentes", `schema.schema_id` sem versão, botão Excluir com ícone `Trash2`, state `targetSchema`) em `docuparse-project/frontend/src/main.jsx` — inserir após `ConfigList` (~linha 3478)
- [X] T011 [US3] Criar componente `DeleteSchemaModal` (exibe nome do schema, botões Cancelar/Excluir vermelho, estado de loading, verificação de proteção de ID sem chamar API, tratamento de erros da API com mensagem ao usuário) em `docuparse-project/frontend/src/main.jsx` — inserir após `SchemaList` (depende de T010)
- [X] T012 [US3] Substituir `<ConfigList title="Schemas existentes" items={schemas} primaryKey="schema_id" secondaryKey="version" />` por `<SchemaList schemas={schemas} onDeleted={onChanged} />` em `docuparse-project/frontend/src/main.jsx` (~linha 2443, depende de T010 e T011)

**Checkpoint**: US3 completa e testável independentemente — backend e frontend implementados.

---

## Phase 5: Polish & Validação Final

**Purpose**: Confirmar integridade do build após todas as mudanças

- [X] T013 Executar `npm run build` em `docuparse-project/frontend/` e confirmar zero erros e zero warnings de lint

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — iniciar imediatamente
- **US1 (Phase 2)**: Depende apenas do Setup — bloqueante para validar baseline
- **US2 (Phase 3)**: Independente de US1 e US3 — pode iniciar após Setup
- **US3 (Phase 4)**: Independente de US1 e US2 — pode iniciar após Setup
- **Polish (Phase 5)**: Depende de todas as user stories concluídas

### User Story Dependencies

- **US1 (P1)**: Sem dependências entre stories — pode começar após Setup
- **US2 (P2)**: Sem dependências entre stories — pode começar após Setup
- **US3 (P3)**: Sem dependências entre stories — pode começar após Setup; T011 depende de T010; T012 depende de T010 e T011

### Parallel Opportunities

- **T002 e T003** (US1): [P] — tocam linhas ~2951 e ~3042, sem sobreposição, podem ser editados em paralelo por implementadores diferentes
- **T009 e T010** (US3): [P] — arquivos diferentes (`views.py` vs `main.jsx`), totalmente independentes
- **T008** (US2): [P] com T004-T007 — seção ~3166 (ExamplesEditor) é independente da região ~2404-2444 (setup tab)

---

## Parallel Example: User Story 3

```bash
# Backend e frontend podem ser implementados em paralelo:
Task T009: "Adicionar DELETE em schema_config_detail_view em views.py"
Task T010: "Criar SchemaList component em main.jsx"

# Após T010 e T009 concluídos:
Task T011: "Criar DeleteSchemaModal em main.jsx"

# Após T010 e T011 concluídos:
Task T012: "Integrar SchemaList substituindo ConfigList em main.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: US1 (T002, T003)
3. **PARAR E VALIDAR**: Abrir documento em validação e confirmar mudanças visuais
4. Continuar com US2 se validado

### Incremental Delivery

1. T001 → Baseline confirmado
2. T002 + T003 → US1 entregue (remoção de ruído visual na validação) ✓
3. T004 → T008 → US2 entregue (configurações simplificadas) ✓
4. T009 + T010 → T011 → T012 → US3 entregue (exclusão de modelos) ✓
5. T013 → Build limpo confirmado

---

## Notes

- [P] = arquivos diferentes ou seções distantes no mesmo arquivo sem risco de conflito
- US1 e US2 são exclusivamente frontend (`main.jsx`); US3 envolve também `views.py`
- Estados internos (`referenceReview`, `schemaForm.tenant_slug`, `schemaForm.version`, `schemaForm.status`) devem ser preservados mesmo onde o campo visual é removido — apenas o render é suprimido
- `PROTECTED_SCHEMA_IDS` deve ser definido no frontend como constante e replicado no backend como lista Python — ambas as camadas devem validar independentemente
- Após cada task de edição em `main.jsx`, verificar que o arquivo continua parseable (sem JSX quebrado) antes de avançar para a próxima task
