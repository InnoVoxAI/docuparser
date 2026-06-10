# Implementation Plan: Workflow de Aprovação e Rejeição de Documentos

**Branch**: `002-doc-approval-rejection` | **Date**: 2026-06-03
**Spec**: [workflow-approval-rejection.md](../specs/workflow-approval-rejection.md)

---

## Summary

Implementação do fluxo completo de aprovação e rejeição de documentos após extração de campos. O backend já possui os modelos `Document` (com status APPROVED/REJECTED) e `ValidationDecision` (com `notes` e `created_at`), além de um endpoint `/validate` funcional. A maior parte do trabalho consiste em: (1) adicionar guardas de validação ao endpoint existente, (2) expor datas de decisão via serializer, (3) criar o endpoint e a view de Aprovados no frontend.

---

## Technical Context

**Backend**: Django + Django REST Framework, Python 3.10, PostgreSQL
**Frontend**: React 18 + Vite (SPA single-file `main.jsx`), Tailwind CSS
**Storage**: LocalStorage (arquivos locais em `DOCUPARSE_LOCAL_STORAGE_DIR`)
**Testing**: pytest (backend), sem framework de testes frontend configurado
**Auth Pattern**: Header `Authorization: Bearer {DOCUPARSE_INTERNAL_SERVICE_TOKEN}` para endpoints internos
**Project Type**: Aplicação web fullstack com backend Django e SPA React

---

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| I. Code Quality — funções ≤ 50 linhas | ✅ PASS | Guardas adicionadas ao `document_validation_view` não excedem o limite; novos componentes React menores que 50 linhas cada |
| I. Code Quality — sem dead code | ✅ PASS | Nenhum código removido sem substituto |
| II. Testing Standards — integration tests obrigatórios para API | ⚠️ REQUIRED | Novos testes de integração necessários para as guardas de validação |
| II. Testing Standards — unit tests para lógica de negócio | ⚠️ REQUIRED | Guard de extração e validação de notes precisam de cobertura |
| III. UX Consistency — estados de loading/error visíveis | ⚠️ REQUIRED | Frontend deve mostrar erro claro ao bloquear aprovação/rejeição |
| IV. Performance — endpoints não-processamento < 200ms p95 | ✅ PASS | Nenhuma operação pesada nova; prefetch_related já em uso |

---

## Análise de Impacto

### O que já existe e funciona

| Componente | Estado Atual | Uso na Feature |
|------------|-------------|----------------|
| `Document.Status.APPROVED` / `REJECTED` | ✅ Existe | Reutilizado sem alteração |
| `ValidationDecision` model | ✅ Existe | `notes` = motivo de rejeição; `created_at` = data da decisão |
| `document_validation_view` | ✅ Existe | Estendido com guardas de validação |
| `document_reprocess_ocr_view` | ✅ Existe | Reutilizado sem alteração |
| `document_delete_view` | ✅ Existe | Reutilizado sem alteração |
| `DocumentListSerializer.rejection_notes` | ✅ Existe | Campo de exibição na tela Rejeitados |
| `RejectedView` (frontend) | ✅ Existe | Extendido com "Visualizar Motivo" e data de rejeição |
| Botões Aprovar/Rejeitar (frontend) | ✅ Existe | Guardas adicionadas no cliente |
| `notes` state no ValidationView | ✅ Existe | Renomeado semanticamente para motivo de rejeição |

### O que precisa ser criado ou modificado

| Componente | Ação | Impacto |
|------------|------|---------|
| `document_validation_view` | Modificar — adicionar 2 guardas | Baixo — apenas validações novas |
| `DocumentListSerializer` | Modificar — adicionar `decision_date` | Baixo — novo campo computado read-only |
| `documents_inbox_view` | Modificar — adicionar prefetch para approved decisions | Baixo — performance melhorada |
| `ApprovedView` (frontend) | Criar — novo componente React | Médio — nova tela completa |
| `ValidationView.submitDecision` | Modificar — guardas client-side | Baixo — validação adicional |
| `NAV_ITEMS` (frontend) | Modificar — adicionar 'approved' | Mínimo — uma linha |
| Textarea "Notas de validacao" | Modificar — label contextual | Mínimo — texto de placeholder |

### Arquivos impactados

```
docuparse-project/
├── backend-core/
│   └── documents/
│       ├── serializers.py          # Adicionar decision_date ao DocumentListSerializer
│       └── views.py                # Adicionar guardas ao document_validation_view
└── frontend/
    └── src/
        └── main.jsx                # ApprovedView + guardas + NAV_ITEMS
```

**Nenhuma migração de banco de dados é necessária.**

---

## Alterações no Banco de Dados

### Situação Atual

O modelo `Document` já possui:
- `status` com `APPROVED` e `REJECTED` como valores válidos
- `updated_at` (proxy aproximado para data de decisão)

O modelo `ValidationDecision` já possui:
- `notes` (TextField, blank=True) — usado como motivo de rejeição
- `created_at` (DateTimeField, auto_now_add) — timestamp exato da decisão

### Decisão: Sem migração de banco de dados

Não é necessário adicionar campos `approved_at` ou `rejected_at` ao modelo `Document`. O `ValidationDecision.created_at` já provê o timestamp exato de cada decisão, e pode ser exposto via serializer sem overhead de migração.

**Justificativa**: Evitar migration minimiza risco de regressão e mantém o plano incremental. O `updated_at` do Document serve como proxy de curto prazo; o `ValidationDecision.created_at` é a fonte definitiva de data de decisão.

**Risco futuro**: Se houver necessidade de filtragem por `approved_at` via ORM (ex: relatórios), uma migração futura para adicionar o campo ao Document será mais simples que resolver via JOIN. Documentar como débito técnico.

---

## Alterações nos Modelos de Domínio

### `ValidationDecision` — Sem alterações no modelo

O modelo já possui todos os campos necessários. A única mudança é semântica: o campo `notes` deve ser tratado como `rejection_reason` quando a decisão é `rejected`. Não é necessário adicionar um novo campo ou renomear — o campo existente é usado de forma polimórfica.

### `Document.Status` — Sem alterações

O conceito de "PENDENTE" na UI corresponde a qualquer documento cujo status não seja `APPROVED` ou `REJECTED`. Os status intermediários (`RECEIVED`, `OCR_COMPLETED`, `EXTRACTION_COMPLETED`, `VALIDATION_PENDING`) todos representam documentos aguardando decisão. Não é necessário adicionar um novo status `PENDING`.

**Consequência para a Inbox**: O filtro correto para a Inbox é `status NOT IN (APPROVED, REJECTED)` ou equivalentemente `status IN (RECEIVED, OCR_COMPLETED, OCR_FAILED, LAYOUT_CLASSIFIED, EXTRACTION_COMPLETED, VALIDATION_PENDING)`. O frontend já implementa este filtro como allowlist na linha 185 do `main.jsx`.

---

## Alterações nos Serviços de Negócio

### `document_validation_view` — Adicionar duas guardas

**Localização**: `docuparse-project/backend-core/documents/views.py`

#### Guarda 1: Extração deve estar concluída

Antes de processar qualquer decisão (approved ou rejected), o sistema deve verificar se o documento possui um `ExtractionResult` associado. Se não existir, retornar HTTP 422 com mensagem descritiva.

**Condição de bloqueio**: `not hasattr(document, 'extraction_result')` ou `ExtractionResult` não existe para o documento.

**Resposta de erro**: `HTTP 422 Unprocessable Entity` com `{"detail": "Extração de campos não concluída. Execute a extração antes de aprovar ou rejeitar."}`

#### Guarda 2: Motivo de rejeição obrigatório

Quando a decisão é `rejected`, o campo `notes` (motivo de rejeição) não pode estar vazio ou conter apenas espaços em branco.

**Condição de bloqueio**: `decision == 'rejected'` e `not notes.strip()`

**Resposta de erro**: `HTTP 400 Bad Request` com `{"detail": "Motivo da rejeição é obrigatório."}`

#### Posicionamento das guardas

As guardas devem ser executadas **antes** de criar o `ValidationDecision`, logo após a validação do campo `decision`. A ordem correta:

1. Validação do campo `decision` (já existe)
2. **[NOVO]** Guarda de extração concluída
3. **[NOVO]** Guarda de notas obrigatórias para rejeição
4. Busca do usuário (já existe)
5. Criação do ValidationDecision (já existe)
6. Transição de status (já existe)

### `documents_inbox_view` — Sem alterações na lógica

O endpoint já suporta `?status=APPROVED` e `?status=REJECTED` via o filtro de query params existente. As listas de aprovados e rejeitados podem ser obtidas via estes parâmetros, sem necessidade de novos endpoints.

O prefetch de `_prefetched_rejection_decisions` já está implementado. Adicionar um prefetch análogo para approved decisions (necessário para expor `decision_date` de documentos aprovados via serializer) deve ser feito no mesmo queryset.

---

## Alterações na API

### Endpoint modificado: `POST /documents/{document_id}/validate`

**Nenhuma mudança de contrato externo** — o endpoint mantém os mesmos parâmetros e respostas de sucesso. Apenas novas respostas de erro são adicionadas.

| Cenário | Status HTTP | Resposta |
|---------|-------------|----------|
| Sem extração concluída | 422 | `{"detail": "Extração de campos não concluída..."}` |
| Rejeição sem motivo | 400 | `{"detail": "Motivo da rejeição é obrigatório."}` |
| Decisão inválida | 400 | `{"detail": "Invalid decision"}` (já existe) |
| Sucesso | 201 | `ValidationDecisionSerializer` (já existe) |

### Endpoint sem alterações: `GET /documents`

Já suporta filtragem por status via `?status=`. Exemplos de uso:
- `GET /documents` → todos os documentos (Inbox usa filtro client-side)
- `GET /documents?status=APPROVED` → documentos aprovados
- `GET /documents?status=REJECTED` → documentos rejeitados

### Serializer modificado: `DocumentListSerializer`

Adicionar campo `decision_date` (read-only, computed):

```
decision_date: ISO 8601 datetime | null
```

Derivado de: `ValidationDecision` mais recente associada ao documento (qualquer tipo de decisão), expondo seu `created_at`. Segue o mesmo padrão do campo `rejection_notes` já existente.

**Impacto no prefetch**: Adicionar ao queryset de `documents_inbox_view` um `Prefetch` para `validation_decisions` (todas as decisões, não apenas rejected) com `to_attr="_prefetched_decisions"`, permitindo que o serializer calcule `decision_date` sem N+1 queries.

---

## Alterações no Frontend

### 1. Adicionar "Aprovados" ao menu de navegação

**Arquivo**: `docuparse-project/frontend/src/main.jsx`

Adicionar item `{ id: 'approved', label: 'Aprovados', icon: CheckCircle2 }` ao array `NAV_ITEMS`. A posição recomendada é entre "Inbox" e "Dashboard", ou após "Rejeitados" — a ser decidida junto ao usuário.

### 2. Criar componente `ApprovedView`

**Arquivo**: `docuparse-project/frontend/src/main.jsx`

Componente similar ao `RejectedView` já existente. Exibe uma tabela com:

| Coluna | Fonte dos dados |
|--------|-----------------|
| Documento | `document.original_filename \|\| document.id` |
| Status | `<StatusBadge status={document.status} />` |
| Data de Aprovação | `formatDate(document.decision_date \|\| document.updated_at)` |

Sem ações (documentos aprovados não possuem ações nesta versão). Estado vazio: "Nenhum documento aprovado."

### 3. Criar `approvedDocuments` computed array

Adicionar ao hook principal (onde `rejectedDocuments` já existe):

```js
const approvedDocuments = useMemo(
    () => documents.filter((d) => d.status === 'APPROVED'),
    [documents],
)
```

### 4. Conectar `ApprovedView` ao roteamento

No render principal, adicionar case para `activeView === 'approved'`, passando `approvedDocuments` como prop.

### 5. Guardas client-side em `submitDecision`

**Localização**: função `submitDecision` (~linha 816 do `main.jsx`)

Adicionar duas validações antes do `api.post`:

**Guarda de extração**:
- Se `selectedDocument.extraction_result` for nulo ou ausente, exibir mensagem de erro (via `setSubmitError` ou similar) e interromper sem chamar a API.
- Mensagem: "Execute a extração de campos antes de aprovar ou rejeitar."

**Guarda de notas na rejeição**:
- Se `decision === 'rejected'` e `notes.trim() === ''`, exibir mensagem de erro e interromper.
- Mensagem: "O motivo da rejeição é obrigatório."

### 6. Melhorar a área de notas no ValidationView

**Situação atual**: `placeholder="Notas de validacao"` — genérico.

**Mudança**: Alterar o placeholder e o comportamento visual para ser contextual:
- Quando o documento está sendo aprovado: o campo `notes` é opcional.
- O `placeholder` deve ser: `"Motivo da rejeição (obrigatório para rejeitar)"`.
- O campo deve ser destacado visualmente (ex: borda vermelha) se o usuário tentar rejeitar sem preencher.

### 7. Melhorar `RejectedRow` com "Visualizar Motivo"

**Situação atual**: `rejection_notes` exibido inline na tabela, truncado.

**Mudança**: Adicionar botão "Visualizar Motivo" que abre um modal simples com o texto completo do motivo. Implementar como estado local `viewingMotivo` no componente `RejectedRow` (boolean), exibindo um overlay/dialog com o texto.

**Alternativa simplificada**: Se o `rejection_notes` for curto, a exibição inline é suficiente. O botão "Visualizar Motivo" pode ser adicionado como tooltip ou `<details>` expansível sem precisar de modal.

### 8. Atualizar data na `RejectedRow`

**Situação atual**: `formatDate(document.updated_at)` — proxy.

**Mudança**: `formatDate(document.decision_date || document.updated_at)` — usa a data exata da decisão quando disponível (via novo campo `decision_date` do serializer).

---

## Estratégia de Testes

### Backend — Testes de integração (obrigatórios por constituição)

**Arquivo alvo**: `docuparse-project/backend-core/documents/tests/` (criar se não existir)

| Teste | Tipo | Cobertura |
|-------|------|-----------|
| Aprovação com extração concluída | Integração | Deve retornar 201 + status APPROVED |
| Aprovação sem extração concluída | Integração | Deve retornar 422 |
| Rejeição com motivo preenchido | Integração | Deve retornar 201 + status REJECTED + notes persistido |
| Rejeição com motivo vazio | Integração | Deve retornar 400 |
| Rejeição com motivo só espaços | Integração | Deve retornar 400 |
| Aprovação de documento já aprovado | Integração | Deve ser bloqueado (400 ou 409) |
| Reprocessamento de documento rejeitado | Integração | Deve transicionar para RECEIVED e reprocessar |
| Listagem filtrada por status APPROVED | Integração | Deve retornar apenas aprovados |
| Listagem filtrada por status REJECTED | Integração | Deve retornar apenas rejeitados |
| `decision_date` no serializer | Unit | Deve retornar created_at da última ValidationDecision |

### Backend — Testes unitários

| Teste | Componente | Cobertura |
|-------|-----------|-----------|
| `get_decision_date` no serializer | `DocumentListSerializer` | None quando sem decisão; created_at quando existe |
| Guard de extração | `document_validation_view` | Retorna 422 quando ExtractionResult ausente |
| Guard de notas | `document_validation_view` | Retorna 400 quando notes vazio na rejeição |

### Frontend — Verificação manual (sem framework de testes configurado)

| Cenário | Critério |
|---------|---------|
| Tentar aprovar sem extração | Mensagem de erro deve aparecer sem chamada API |
| Tentar rejeitar sem motivo | Mensagem de erro deve aparecer sem chamada API |
| Aprovar documento → verificar Inbox | Doc não aparece mais na Inbox |
| Aprovar documento → verificar Aprovados | Doc aparece em Aprovados com data |
| Rejeitar documento → verificar Rejeitados | Doc aparece com motivo correto |
| Clicar "Visualizar Motivo" | Modal/expansão exibe motivo completo |
| Clicar "Reprocessar" em Rejeitados | Doc retorna à Inbox após reprocessamento |
| Clicar "Excluir" em Rejeitados | Doc remove de todas as listas |

---

## Dependências entre Etapas

### Grafo de dependências

```
[B1] Guardas no document_validation_view
  ↓
[B2] Campo decision_date no DocumentListSerializer
  ↓
[F1] ApprovedView + approvedDocuments + NAV_ITEM
[F2] Guardas client-side em submitDecision  ← depende B1 (para mensagens de erro alinhadas)
[F3] Atualizar RejectedRow (decision_date, Visualizar Motivo)  ← depende B2

[T1] Testes unitários das guardas  ← depende B1
[T2] Testes de integração dos endpoints  ← depende B1 + B2
```

### Ordem recomendada de execução

#### Fase 1 — Backend (pré-requisito para F2 e testes)
1. **B1**: Adicionar guardas ao `document_validation_view`
   - Guarda de extração (422 se sem ExtractionResult)
   - Guarda de notas (400 se rejected + notes vazio)
2. **B2**: Adicionar `decision_date` ao `DocumentListSerializer`
   - Adicionar prefetch ao queryset do `documents_inbox_view`
   - Adicionar `get_decision_date` ao serializer

#### Fase 2 — Frontend (paralelo após Fase 1)
3. **F1**: `approvedDocuments`, `ApprovedView`, NAV_ITEM 'approved', roteamento
4. **F2**: Guardas client-side no `submitDecision` + atualizar placeholder do textarea
5. **F3**: Atualizar `RejectedRow` (decision_date + Visualizar Motivo)

#### Fase 3 — Testes
6. **T1**: Testes unitários das guardas no backend
7. **T2**: Testes de integração dos endpoints modify
8. **T3**: Verificação manual do fluxo completo

### Paralelismo possível
- B1 e B2 podem ser desenvolvidos em paralelo (arquivos distintos na mesma função view vs serializer)
- F1, F2 e F3 podem ser desenvolvidos em paralelo após B1 estar mergeado
- T1 e T3 (manual) podem ser executados em paralelo com T2

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| ExtractionResult não carregado no `select_related` do `document_validation_view` | Médio | Alto (N+1 ou AttributeError) | Adicionar `ExtractionResult` ao `select_related` no view |
| Frontend ainda usa `document.updated_at` como data de decisão | Baixo | Baixo | Usar `decision_date ?? updated_at` como fallback |
| Rejeição de documento que já foi decidido | Médio | Médio | Adicionar verificação de status no view (retornar 409 se já APPROVED/REJECTED) |
| Reprocessamento de OCR silenciosamente falha | Baixo | Médio | `document_reprocess_ocr_view` já trata exceções; verificar resposta de erro no frontend |

---

## Dívidas Técnicas Identificadas

1. **Dívida**: A inbox carrega TODOS os documentos e filtra no cliente — potencial problema de performance com volume alto.
   **Recomendação futura**: Filtrar no backend com `status__not_in` query param ou endpoint dedicado de Inbox.

2. **Dívida**: A aprovação/rejeição não verifica se o documento já foi decidido anteriormente — pode criar múltiplos `ValidationDecision` para o mesmo documento.
   **Recomendação futura**: Adicionar constraint ou verificação de status antes de criar nova decisão.

3. **Dívida**: `approved_at` e `rejected_at` derivados de `ValidationDecision.created_at` via serializer — se necessitar filtragem por data no ORM, será preciso migrar para campos diretos no Document.
   **Recomendação futura**: Migration para adicionar campos de data ao Document quando relatórios forem necessários.
