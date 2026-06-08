# Data Model: Workflow de Aprovação e Rejeição de Documentos

**Feature**: [workflow-approval-rejection.md](specs/workflow-approval-rejection.md)
**Branch**: `002-doc-approval-rejection` | **Date**: 2026-06-03

---

## Entidades Relevantes

### Document (existente — sem alterações de schema)

| Campo | Tipo | Observação |
|-------|------|------------|
| `id` | UUID | PK |
| `status` | CharField (choices) | `APPROVED` e `REJECTED` já existem |
| `updated_at` | DateTimeField | Proxy para data da decisão (substituído por `decision_date` no serializer) |

**Status flow para esta feature**:

```
RECEIVED → OCR_COMPLETED → EXTRACTION_COMPLETED
                                    ↓
                             [extração presente]
                                    ↓
                          APPROVED ←→ REJECTED
                                         ↓
                                  [Reprocessar OCR]
                                         ↓
                                      RECEIVED
```

---

### ValidationDecision (existente — sem alterações)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|------------|-----------|
| `id` | UUID | ✓ | PK |
| `document` | FK(Document) | ✓ | Documento decidido |
| `decided_by` | FK(User) | ✓ | Operador que tomou a decisão |
| `decision` | CharField (choices) | ✓ | `approved` / `rejected` / `corrected` |
| `notes` | TextField | Sim (para rejeição) | Motivo da rejeição quando `decision='rejected'` |
| `created_at` | DateTimeField | auto | Timestamp exato da decisão |

**Regra de negócio**: quando `decision='rejected'`, `notes` NÃO PODE ser vazio ou apenas espaços em branco. Esta regra é enforced no backend (`document_validation_view`).

---

### ExtractionResult (existente — sem alterações)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `document` | OneToOneFK(Document) | Relação 1:1 |
| `fields` | JSONField | Campos extraídos |

**Presença obrigatória**: Para que um documento possa ser aprovado ou rejeitado, deve existir um `ExtractionResult` associado. Se não existir, o sistema retorna HTTP 422.

---

## Campo Virtual: `decision_date`

Não é um campo de banco de dados. É um campo computado adicionado ao `DocumentListSerializer`:

- **Fonte**: `ValidationDecision.created_at` da decisão mais recente (qualquer tipo)
- **Tipo na resposta API**: ISO 8601 datetime string ou `null`
- **Uso**: exibir data de aprovação na tela "Aprovados" e data de rejeição na tela "Rejeitados"

---

## Diagrama de Relações

```
Document 1 ──── * ValidationDecision
    │
    └─── 0..1 ExtractionResult
```

---

## Transições de Estado

| Estado Anterior | Ação | Estado Novo | Pré-condição |
|----------------|------|-------------|-------------|
| Qualquer (não APPROVED/REJECTED) | Aprovar | APPROVED | ExtractionResult presente |
| Qualquer (não APPROVED/REJECTED) | Rejeitar | REJECTED | ExtractionResult presente + notes não vazio |
| REJECTED | Reprocessar OCR | RECEIVED → (OCR flow) | — |
| Qualquer | Excluir | (removido) | — |
