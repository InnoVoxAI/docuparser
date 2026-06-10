# Research: Workflow and Permissions Improvements

**Feature**: `004-workflow-perms-improvements`
**Date**: 2026-06-08

---

## Decision 1: Identificação de Perfil de Desenvolvedor (FR-010)

**Decision**: Usar a permissão `operations.access` já existente.

**Rationale**: A análise do código confirmou que o frontend (`main.jsx`, linha 48) já gatea o menu "Operações" com `operations.access`. O componente `PermissionGuard` e o array `NAV_ITEMS` já estão corretamente configurados. Qualquer role que não possua `operations.access` no banco não verá o item no menu. Não há gap de implementação no backend de permissões.

**Alternatives considered**:
- `is_developer` flag no UserProfile: requer migração de modelo + UI de admin modificada.
- Role reservada "Desenvolvedor": menos flexível (obriga nome exato, sem variações).

**Gap encontrado**: O acesso direto à URL não é relevante pois a aplicação é SPA — não há URL de "Operações" acessível diretamente sem passar pelo frontend.

---

## Decision 2: Extração Automática após OCR (FR-002)

**Decision**: Após `process_document_ocr` concluir com sucesso, chamar `auto_extract_after_ocr(document)` síncronamente dentro do thread do OCR.

**Rationale**: A função `process_document_ocr` já existe em `documents/services/ocr_processor.py`. O `LangExtractClient` já existe em `documents/services/langextract_client.py`. O `LayoutConfig` permite mapear `document.layout` → `SchemaConfig`. A extração automática deve ser controlada por uma flag de ambiente `DOCUPARSE_AUTO_PROCESS_EXTRACTION` (padrão `true`), análoga ao `DOCUPARSE_AUTO_PROCESS_OCR` existente.

**Flow**:
```
OCR concluído (document.status = OCR_COMPLETED)
  → detect layout (document.layout ou document.document_type)
  → buscar LayoutConfig ativo para esse layout
  → buscar SchemaConfig associado
  → chamar LangExtractClient.extract_with_schema()
  → salvar ExtractionResult (update_or_create)
  → transicionar status para VALIDATION_PENDING
```

**Edge cases**:
- Sem LayoutConfig para o layout detectado → skip silencioso, documento fica em OCR_COMPLETED
- LangExtract falha → logar warning, documento fica em OCR_COMPLETED (não bloquear OCR)

**Alternatives considered**:
- Django signals (post_save em Document): mais desacoplado mas difícil de testar e debugar.
- Celery task: overhead desnecessário dado que o sistema já usa threads para OCR.

---

## Decision 3: Processamento em Fila (FR-003)

**Decision**: Usar um `ThreadPoolExecutor` com worker único (max_workers=1 por padrão, configurável via `DOCUPARSE_PROCESSING_WORKERS`) para serializar o processamento OCR+extração.

**Rationale**: O sistema já usa `threading.Thread` para processar OCR em background. Substituir por `ThreadPoolExecutor` global permite:
- Limitar concorrência (evitar sobrecarga do backend-ocr).
- Isolar falhas individuais via futures.
- Configurar capacidade via variável de ambiente.
- Sem nova infraestrutura (não requer Celery/Redis extra).

**Implementation**: Criar `documents/services/processing_queue.py` com um executor compartilhado. `start_document_ocr_thread` passa a submeter ao executor.

**Alternatives considered**:
- Celery + Redis: mais robusto para produção, mas adiciona dependência e complexidade de setup.
- Redis Streams: o sistema usa `docuparse_events` com Redis Streams, mas é para eventos inter-serviço, não para OCR interno.

---

## Decision 4: Datas de Aprovação e Rejeição (FR-005)

**Decision**: Adicionar campos `approved_at` e `rejected_at` ao `DocumentListSerializer`.

**Rationale**: O modelo `ValidationDecision` já persiste decisões com `created_at`. O serializer atual tem `decision_date` (data da última decisão qualquer) e `rejection_notes`. Adicionar campos separados `approved_at` e `rejected_at` é uma extensão de serializer pura — sem migração, sem novo campo no banco.

**Query**: Filtrar `validation_decisions` prefetchadas por `decision='approved'` e `decision='rejected'` separadamente.

**Alternatives considered**:
- Adicionar campos `approved_at`/`rejected_at` ao modelo `Document`: requer migração e duplica dado já em `ValidationDecision`.

---

## Decision 5: Popup de Documentos Rejeitados no Dashboard (FR-006)

**Decision**: Adicionar estado `rejectedModal` no componente `Dashboard` do frontend. Clicar em um documento REJEITADO abre um modal overlay com motivo, data e botões de ação.

**Rationale**: A infraestrutura já existe: `rejection_notes` e `decision_date` já são retornados pelo serializer. Os handlers `handleReprocessDocument` e `handleDeleteDocument` já existem no `App`. O modal segue o padrão já usado no `GerenciarUsuarios` e `GerenciarRoles` (div com `fixed inset-0 bg-black/40`).

**Changes**: 
- `Dashboard` recebe props `onReprocess`, `onDelete` do `App`.
- Adicionar `DocumentTable` clickable para documentos REJECTED.
- Modal com: nome do arquivo, motivo (ou "Motivo não informado"), data/hora, botão Reprocessar, botão Excluir.

---

## Decision 6: Nomes Legíveis de Permissões (FR-004)

**Decision**: Atualizar `RoleListSerializer.get_permissions` para retornar lista de `{code, description}` em vez de lista de códigos. Atualizar frontend para exibir `description` na tabela de roles.

**Rationale**: O endpoint `GET /permissions` já retorna `{code, description}` (via `permission_views.py`). O modal de criação/edição de roles no frontend já usa `p.description` nos checkboxes. O gap restante é: (1) a tabela de roles mostra os códigos em vez das descrições; (2) a lógica de toggle/save usa `permission_codes` (códigos) — que deve ser mantida para a API. A solução é: serializer retorna lista de objetos `{code, description}`, frontend exibe `description` e usa `code` para submit.

**Backward compatibility**: O campo `permission_codes` no payload de criação/edição de roles continua usando códigos — sem alteração no backend de escrita.
