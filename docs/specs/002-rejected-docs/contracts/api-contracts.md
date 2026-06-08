# API Contracts: Workflow de Aprovação e Rejeição de Documentos

**Feature**: [workflow-approval-rejection.md](../specs/workflow-approval-rejection.md)
**Branch**: `002-doc-approval-rejection` | **Date**: 2026-06-03

---

## Endpoint Modificado: POST /documents/{document_id}/validate

Aprova ou rejeita um documento. Este endpoint já existe; a modificação adiciona dois novos erros e o campo `notes` passa a ser obrigatório para `decision=rejected`.

### Request

```
POST /api/ocr/documents/{document_id}/validate
Content-Type: application/json
Authorization: Bearer {token}

{
  "decision": "approved" | "rejected" | "corrected",
  "notes": "string",           // obrigatório quando decision=rejected
  "corrected_fields": {}       // opcional
}
```

### Respostas

| HTTP | Condição | Body |
|------|----------|------|
| 201 Created | Decisão registrada com sucesso | `ValidationDecisionSerializer` |
| 400 Bad Request | Decisão inválida | `{"detail": "Invalid decision"}` |
| 400 Bad Request | Rejeição sem motivo | `{"detail": "Motivo da rejeição é obrigatório."}` |
| 404 Not Found | Documento não existe | `{"detail": "Not found."}` |
| 422 Unprocessable Entity | Extração não concluída | `{"detail": "Extração de campos não concluída. Execute a extração antes de aprovar ou rejeitar."}` |

### Contrato de sucesso (201)

```json
{
  "id": "uuid",
  "document_id": "uuid",
  "decided_by_id": "uuid",
  "decision": "approved",
  "corrected_fields": {},
  "notes": "",
  "created_at": "2026-06-03T12:00:00Z"
}
```

---

## Endpoint Existente: GET /documents

Retorna lista de documentos. Suporta filtragem por status via query param.

### Usos relevantes para esta feature

```
GET /api/ocr/documents                    # Todos os documentos (Inbox filtra client-side)
GET /api/ocr/documents?status=APPROVED    # Tela "Aprovados"
GET /api/ocr/documents?status=REJECTED    # Tela "Rejeitados"
```

### Campo adicionado ao response: `decision_date`

```json
{
  "id": "uuid",
  "status": "APPROVED",
  "original_filename": "NF_VANDA.pdf",
  "rejection_notes": null,
  "decision_date": "2026-06-03T11:45:00Z",  // NOVO — null se nenhuma decisão registrada
  ...
}
```

---

## Endpoint Existente: POST /documents/{document_id}/reprocess-ocr

Reinicia o processamento OCR de um documento rejeitado.

### Request

```
POST /api/ocr/documents/{document_id}/reprocess-ocr
Authorization: Bearer {token}
(sem body)
```

### Respostas

| HTTP | Condição |
|------|----------|
| 200 OK | OCR reprocessado — retorna DocumentDetailSerializer |
| 404 Not Found | Documento não encontrado |
| 404 Not Found | Arquivo original não encontrado |
| 502 Bad Gateway | Falha no processamento OCR |

---

## Endpoint Existente: DELETE /documents/{document_id}/delete

Remove o documento permanentemente.

### Request

```
DELETE /api/ocr/documents/{document_id}/delete
Authorization: Bearer {token}
```

### Resposta

| HTTP | Condição |
|------|----------|
| 204 No Content | Documento excluído |
| 404 Not Found | Documento não encontrado |
