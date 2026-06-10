# Data Model: Workflow and Permissions Improvements

**Feature**: `004-workflow-perms-improvements`
**Date**: 2026-06-08

---

## Nota sobre Alterações de Modelo

Esta feature **não requer novas migrações de banco de dados**. Todas as entidades necessárias já existem. As mudanças são exclusivamente em:
- Serializers (camada de serialização)
- Services (lógica de negócio)
- Frontend (interface)

---

## Entidades Existentes Relevantes

### Document

| Campo | Tipo | Relevância nesta feature |
|-------|------|--------------------------|
| `id` | UUID | Identificador |
| `status` | CharField | Estado atual; `REJECTED`, `APPROVED`, `OCR_COMPLETED` |
| `layout` | CharField | Usado para encontrar LayoutConfig na extração automática |
| `document_type` | CharField | Fallback para identificar schema na extração automática |
| `raw_text_uri` | CharField | URI do texto OCR; precisa existir para auto-extração |

**Estado machine relevante para FR-002/FR-003:**
```
RECEIVED → [OCR thread] → OCR_COMPLETED → [auto-extract thread] → VALIDATION_PENDING
```

---

### ValidationDecision

| Campo | Tipo | Relevância nesta feature |
|-------|------|--------------------------|
| `document` | FK(Document) | Relacionamento |
| `decision` | CharField | `approved`, `rejected`, `corrected` |
| `notes` | TextField | Motivo da rejeição (FR-006) |
| `created_at` | DateTimeField | Data de aprovação/rejeição (FR-005) |

**Queries novas no serializer:**
- `approved_at`: `ValidationDecision` onde `decision='approved'`, mais recente
- `rejected_at`: `ValidationDecision` onde `decision='rejected'`, mais recente

---

### Permission

| Campo | Tipo | Relevância nesta feature |
|-------|------|--------------------------|
| `code` | CharField | Identificador técnico |
| `description` | CharField | Nome legível — já populado pelo `seed_permissions` |

**Mudança no serializer de Role:** retornar `description` além do `code`.

---

### LayoutConfig → SchemaConfig (para FR-002)

```
document.layout
    → LayoutConfig.filter(layout=document.layout, is_active=True)
    → LayoutConfig.schema_config (FK)
    → SchemaConfig.definition (JSON com campos para extração)
    → SchemaConfig.schema_id + schema_config.version
```

Se nenhum `LayoutConfig` ativo for encontrado para o layout do documento, a extração automática é pulada silenciosamente.

---

## Novos Campos de Serializer (sem migração)

### DocumentListSerializer — campos adicionados

| Campo novo | Fonte | Lógica |
|------------|-------|--------|
| `approved_at` | `ValidationDecision` | Última decisão com `decision='approved'` → `created_at` |
| `rejected_at` | `ValidationDecision` | Última decisão com `decision='rejected'` → `created_at` |

O campo `decision_date` existente é mantido para compatibilidade.

### RoleListSerializer — campo alterado

| Campo | Antes | Depois |
|-------|-------|--------|
| `permissions` | `list[str]` (códigos) | `list[{code, description}]` |

---

## Novo Serviço: ProcessingQueue

**Arquivo**: `docuparse-project/backend-core/documents/services/processing_queue.py`

| Elemento | Descrição |
|----------|-----------|
| `_executor` | `ThreadPoolExecutor(max_workers=DOCUPARSE_PROCESSING_WORKERS)` — instância global |
| `submit_document_processing(document_id)` | Submete OCR + extração automática ao executor |
| `DOCUPARSE_PROCESSING_WORKERS` | Env var (default: `2`) |

**Integração**: `document_received_event_view` e o endpoint de upload passam a chamar `submit_document_processing` em vez de `start_document_ocr_thread`.

---

## Nova Lógica: Auto-extração pós-OCR

**Arquivo**: `docuparse-project/backend-core/documents/services/ocr_processor.py` (adição)

```python
def auto_extract_after_ocr(document: Document) -> None:
    """Tenta extração automática se houver LayoutConfig para o layout do documento."""
    layout_cfg = LayoutConfig.objects.filter(
        tenant=document.tenant, layout=document.layout, is_active=True
    ).select_related("schema_config").first()
    if not layout_cfg:
        return
    # ... chama LangExtractClient, salva ExtractionResult, transiciona status
```

Controlado pela env var `DOCUPARSE_AUTO_PROCESS_EXTRACTION` (default: `true`).
