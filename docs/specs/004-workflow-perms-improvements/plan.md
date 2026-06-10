# Implementation Plan: Workflow and Permissions Improvements

**Branch**: `004-workflow-perms-improvements` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)

**Input**: [docs/specs/004-workflow-perms-improvements/spec.md](spec.md)

---

## Summary

Seis melhorias incrementais no sistema existente sem novas migrações ou nova infraestrutura:
1. **FR-006** — Modal de documento rejeitado no Dashboard (popup com motivo, data, reprocessar, excluir)
2. **FR-005** — Colunas `approved_at` / `rejected_at` separadas no Dashboard e tela Aprovados
3. **FR-002** — Extração automática de campos após conclusão do OCR
4. **FR-003** — Fila de processamento com concorrência controlada via ThreadPoolExecutor
5. **FR-010** — Tela Operações já restrita via `operations.access` (gap mínimo: verificar e documentar)
6. **FR-004** — Permissões exibidas com nomes legíveis na tela de Roles

Todas as mudanças ocorrem em arquivos existentes: `documents/serializers.py`, `documents/services/ocr_processor.py`, um novo `documents/services/processing_queue.py`, e `frontend/src/main.jsx`.

---

## Technical Context

**Language/Version**: Python 3.10 (backend), JavaScript/React (frontend, single file)

**Primary Dependencies**:
- Django 4.x + Django REST Framework
- `djangorestframework-simplejwt` (auth)
- `docuparse_storage` (LocalStorage / MinIO)
- `docuparse_events` (event bus Redis/file)
- React 18 + Vite + Axios + Tailwind CSS + Lucide React

**Storage**: PostgreSQL (Docker) / SQLite (local) — seleção via `POSTGRES_HOST` env var

**Testing**: pytest (backend), sem testes automatizados de frontend

**Target Platform**: Linux, Docker Compose

**Project Type**: Web application (monorepo: Django backend + React SPA frontend)

**Performance Goals**: Endpoints não-processamento ≤ 200ms (p95); OCR ≤ 30s (p95)

**Constraints**: Sem nova infraestrutura; ThreadPoolExecutor usa recursos existentes

**Scale/Scope**: Processamento de até 10 documentos simultâneos sem degradação

---

## Constitution Check

| Princípio | Status | Observação |
|-----------|--------|------------|
| I. Code Quality — funções ≤ 50 linhas | ✅ PASS | `auto_extract_after_ocr` e `processing_queue` serão mantidos pequenos |
| I. Code Quality — type hints | ✅ PASS | Todos os novos módulos Python usarão type hints |
| I. Code Quality — sem dead code | ✅ PASS | Nenhum código legado removido sem substituto |
| II. Testing — unit tests para lógica não-trivial | ⚠️ ATENÇÃO | `auto_extract_after_ocr` e `processing_queue` devem ter testes unitários |
| II. Testing — mocks para serviços externos | ✅ PASS | LangExtractClient e OCRClient são mockados em testes existentes |
| III. UX — loading/success/error states | ✅ PASS | Modal de rejeição terá estados explícitos |
| III. UX — responsive design | ✅ PASS | Modal seguirá padrão de `fixed inset-0` já estabelecido |
| IV. Performance — endpoints ≤ 200ms | ✅ PASS | Novos campos no serializer são derivados de prefetch existente |

**Sem violações críticas.** O único ponto de atenção é cobertura de testes para os dois novos serviços backend.

---

## Project Structure

### Documentation (this feature)

```text
docs/specs/004-workflow-perms-improvements/
├── plan.md              # Este arquivo
├── research.md          # Decisões técnicas e alternativas
├── data-model.md        # Entidades e mudanças de serializer
├── spec.md              # Especificação funcional
├── checklists/
│   └── requirements.md  # Checklist de qualidade (100% ✅)
└── tasks.md             # Gerado por /speckit-tasks
```

### Source Code (arquivos a modificar)

```text
docuparse-project/
├── backend-core/
│   └── documents/
│       ├── serializers.py                    # FR-004, FR-005: novos campos e formato de permissões
│       ├── views.py                          # FR-003: usar processing_queue em vez de thread direto
│       └── services/
│           ├── ocr_processor.py              # FR-002: adicionar auto_extract_after_ocr()
│           └── processing_queue.py           # FR-003: NOVO — ThreadPoolExecutor global
└── frontend/
    └── src/
        └── main.jsx                          # FR-004, FR-005, FR-006: modal, colunas, display
```

**Structure Decision**: Web application com backend Django e frontend React (monorepo). Todos os arquivos de fonte já existem — esta feature é exclusivamente uma extensão de arquivos existentes, sem criação de novos módulos além de `processing_queue.py`.

---

## Complexity Tracking

Nenhuma violação da constitution requer justificativa. As mudanças são incrementais dentro da estrutura existente.

---

## Implementation Guide por User Story

### US1 — FR-006: Modal de Documento Rejeitado no Dashboard (P1)

**Objetivo**: Clicar em documento REJECTED no Dashboard abre modal com motivo, data, "Reprocessar" e "Excluir".

**Backend** (`documents/serializers.py`):
- Adicionar `approved_at` e `rejected_at` como `SerializerMethodField` em `DocumentListSerializer`.
- `get_rejected_at`: filtra `_prefetched_decisions` por `decision='rejected'` → retorna `created_at.isoformat()`.
- `get_approved_at`: filtra por `decision='approved'` → retorna `created_at.isoformat()`.
- O campo `decision_date` existente é mantido para compatibilidade.

**Frontend** (`frontend/src/main.jsx`):
- Adicionar `rejectedModal` state no componente `App` (ou `Dashboard`).
- `Dashboard` recebe `onReprocess`, `onDelete` como props adicionais.
- Quando `onSelectDocument` for chamado para um documento com `status === 'REJECTED'`, abrir modal.
- Componente `RejectedDocumentModal`: overlay `fixed inset-0 bg-black/40`, card central com:
  - Nome do arquivo
  - Motivo: `doc.rejection_notes || 'Motivo não informado'`
  - Data: `formatDate(doc.rejected_at ?? doc.decision_date)`
  - Botão "Reprocessar" → `onReprocess(doc.id)` + fechar modal
  - Botão "Excluir" → `onDelete(doc.id)` + fechar modal (confirmação já está no handler)
  - Botão "Fechar" (X)

---

### US2 — FR-005: Datas no Dashboard (P2)

**Backend** (`documents/serializers.py`):
- Campos `approved_at` e `rejected_at` são adicionados junto com US1 (mesmos campos).

**Frontend** (`frontend/src/main.jsx`):
- `ApprovedView`: coluna "Data de aprovação" passa a usar `doc.approved_at ?? doc.decision_date`.
- `Dashboard` → `DocumentTable`: adicionar coluna "Decisão em" que exibe `approved_at` ou `rejected_at` conforme o status.
- Para documentos não-decididos: coluna fica vazia (`null` → sem texto, sem erro).

---

### US3 — FR-002: Extração Automática pós-OCR (P3)

**Backend** (`documents/services/ocr_processor.py`):

```python
def auto_extract_after_ocr(document: Document) -> None:
    if not os.environ.get('DOCUPARSE_AUTO_PROCESS_EXTRACTION', 'true').lower() not in {'0', 'false', 'no'}:
        return
    layout_cfg = LayoutConfig.objects.filter(
        tenant=document.tenant,
        layout=document.layout,
        is_active=True,
    ).select_related('schema_config').first()
    if not layout_cfg or not document.raw_text_uri:
        return
    # ler texto bruto do storage
    # chamar LangExtractClient.extract_with_schema()
    # salvar ExtractionResult (update_or_create)
    # document.transition_to(Document.Status.VALIDATION_PENDING)
```

- `process_document_ocr()` chama `auto_extract_after_ocr(document)` após salvar o resultado de OCR.
- Falha na extração automática é capturada com `logger.warning` — não propaga exceção.

**Settings** (`core/settings.py`):
```python
DOCUPARSE_AUTO_PROCESS_EXTRACTION = os.environ.get('DOCUPARSE_AUTO_PROCESS_EXTRACTION', 'true').strip().lower() not in {'0', 'false', 'no'}
```

---

### US4 — FR-003: Processamento em Fila (P4)

**Novo arquivo** (`documents/services/processing_queue.py`):

```python
from concurrent.futures import ThreadPoolExecutor
import os

_MAX_WORKERS = int(os.environ.get('DOCUPARSE_PROCESSING_WORKERS', '2'))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS)

def submit_document_processing(document_id) -> None:
    _executor.submit(_run_processing_safely, document_id)

def _run_processing_safely(document_id) -> None:
    try:
        from documents.services.ocr_processor import process_document_ocr
        process_document_ocr(document_id)  # inclui auto_extract_after_ocr internamente
    except Exception as exc:
        logger.warning('processing_queue_failed', extra={'document_id': str(document_id), 'error': str(exc)})
```

**Integração** (`documents/views.py`):
- `document_received_event_view`: substituir `start_document_ocr_thread(document.id)` por `submit_document_processing(document.id)`.
- `start_document_ocr_thread` pode ser mantida para compatibilidade de chamadas internas ou deprecada.

---

### US5 — FR-010: Restrição da Tela Operações (P5)

**Status**: Já implementado no frontend. O menu "Operações" usa `permission: 'operations.access'` em `NAV_ITEMS` (linha 48 de `main.jsx`) e está protegido por `PermissionGuard` na renderização (linha 519).

**Ação necessária**: Nenhuma mudança de código. Verificar na tabela de permissões que `operations.access` existe no banco (`seed_permissions`) e confirmar que está documentado em `database-guide.md`.

---

### US6 — FR-004: Nomes Legíveis de Permissões (P6)

**Backend** (`users/serializers.py`):
- `RoleListSerializer.get_permissions`: retornar `list[dict]` com `{code, description}` em vez de `list[str]`.

```python
def get_permissions(self, obj: Any) -> list[dict]:
    return list(obj.permissions.values('code', 'description'))
```

**Frontend** (`frontend/src/main.jsx`):
- Tabela de roles (linha 3708): mudar de `(r.permissions || []).join(', ')` para exibir `description`.
  ```jsx
  {(r.permissions || []).map(p => p.description || p.code || p).join(', ')}
  ```
- O `togglePerm` já usa `p.code` (correto — o endpoint de escrita recebe `permission_codes`).
- O `form.permission_codes.includes(p.code)` já está correto.

**Backward compatibility**: Verificar se `r.permissions` retorna objetos `{code, description}` ou ainda strings em outros lugares do frontend. Como `permission_codes` é o campo de escrita e `permissions` é somente de leitura, a mudança é isolada.

---

## Sequence of Implementation

```
1. Backend: DocumentListSerializer — campos approved_at, rejected_at       [US1, US2]
2. Backend: auto_extract_after_ocr() em ocr_processor.py                   [US3]
3. Backend: processing_queue.py + integração em views.py                   [US4]
4. Backend: RoleListSerializer.get_permissions → {code, description}        [US6]
5. Frontend: RejectedDocumentModal + Dashboard clickable                    [US1]
6. Frontend: colunas approved_at/rejected_at em ApprovedView e Dashboard   [US2]
7. Frontend: display description em tabela de roles                         [US6]
8. Verificação: operations.access no banco + documentação                  [US5]
```

**US1 e US2 compartilham o mesmo campo de serializer** — implementar juntos no backend.
**US3 e US4 são sequenciais** — a fila chama o mesmo `process_document_ocr` que agora inclui extração.
**US5 é verificação apenas** — sem código novo.
**US6 é independente** — pode ser implementado em paralelo com qualquer outro.
