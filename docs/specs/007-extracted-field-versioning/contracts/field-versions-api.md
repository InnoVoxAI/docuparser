# API Contract — Extracted Field Versions

Microsserviço: `backend-core` (Django REST). Prefixo de rota interno: `/` (montado no frontend sob `/api/ocr`).
Todas as respostas seguem o envelope da constituição: `{ "data": ..., "error": null | {...}, "meta": {...} }`.
Autorização: `documents.validate` (header de autenticação interno já usado pela app) — FR-026.

---

## 1. Salvar Alterações (criar versão manual)

`PUT /documents/{document_id}/fields`

Cria uma nova versão `MANUAL_EDIT` a partir das edições/remoções/adições do usuário e torna-a ativa (FR-008). Requer confirmação no cliente antes de chamar (FR-007).

### Request body

```json
{
  "base_version_number": 3,
  "fields": [
    { "name": "valor_total", "value": "1234.56" },
    { "name": "vencimento", "value": "2026-07-10" },
    { "name": "fornecedor_novo", "value": "ACME LTDA" }
  ]
}
```

- `base_version_number` (int, obrigatório): número da versão ativa sobre a qual o usuário editou (controle de concorrência otimista — FR-024).
- `fields` (array, obrigatório): lista final de campos após edições/remoções/adições. Campos ausentes em relação à versão base são considerados removidos. Nome vazio é descartado.

### Responses

**201 Created** — nova versão ativa criada.

```json
{
  "data": {
    "version_number": 4,
    "source_type": "MANUAL_EDIT",
    "is_active": true,
    "previous_version_number": 3,
    "created_at": "2026-06-22T14:05:00Z",
    "created_by": "operador@tenant",
    "fields": {
      "valor_total": { "value": "1234.56", "confidence": 1.0 },
      "vencimento": { "value": "2026-07-10", "confidence": 0.92 },
      "fornecedor_novo": { "value": "ACME LTDA", "confidence": 1.0 }
    }
  },
  "error": null,
  "meta": {}
}
```

Notas:
- `valor_total` e `fornecedor_novo` foram alterados/adicionados → `confidence: 1.0` (FR-025/FR-027).
- `vencimento` não foi alterado → mantém confiança da versão base.

**409 Conflict** — versão base não é mais a ativa (FR-024). Nenhuma versão criada.

```json
{
  "data": null,
  "error": {
    "code": "version_conflict",
    "message": "A lista de campos foi atualizada por outro processo. Recarregue a versão ativa antes de salvar."
  },
  "meta": { "active_version_number": 5 }
}
```

**422 Unprocessable Entity** — lista vazia (Edge Case "Remover todos os campos") ou nenhuma alteração.

```json
{ "data": null, "error": { "code": "empty_field_list", "message": "Não é possível salvar uma lista de campos vazia." }, "meta": {} }
```

**403 Forbidden** — usuário sem acesso à função de validação (FR-026).

---

## 2. Consultar Histórico de Versões

`GET /documents/{document_id}/field-versions`

Retorna todas as versões (ativa + anteriores) ordenadas desc por `version_number`. Somente leitura (FR-018–FR-022).

### Response — 200 OK

```json
{
  "data": [
    {
      "version_number": 4,
      "source_type": "MANUAL_EDIT",
      "is_active": true,
      "previous_version_number": 3,
      "created_at": "2026-06-22T14:05:00Z",
      "created_by": "operador@tenant",
      "fields": {
        "valor_total": { "value": "1234.56", "confidence": 1.0 }
      }
    },
    {
      "version_number": 3,
      "source_type": "REPROCESSING",
      "is_active": false,
      "previous_version_number": 2,
      "created_at": "2026-06-22T13:40:00Z",
      "created_by": null,
      "fields": {
        "valor_total": { "value": "1200.00", "confidence": 0.88 }
      }
    }
  ],
  "error": null,
  "meta": { "count": 4, "active_version_number": 4 }
}
```

**404 Not Found** — documento inexistente / fora do tenant.

Estado vazio (documento sem nenhuma extração): `data: []`, `meta.count: 0` (Edge Case "Documento sem extração") — não é erro.

---

## 3. Pontos existentes alterados (comportamento, não nova rota)

Estes endpoints **deixam de sobrescrever** `ExtractionResult.fields` e passam a criar versão via serviço de versionamento.

### `POST /documents/{document_id}/langextract`
- Antes: `ExtractionResult.objects.update_or_create(...)` (sobrescrevia).
- Depois: cria `ExtractionFieldVersion` (`INITIAL_EXTRACTION` se primeira, senão `REPROCESSING`) e sincroniza `ExtractionResult`. Resposta mantém o shape atual (`fields`, `confidence`) por compatibilidade do frontend.

### `POST /documents/{document_id}/validate`
- Antes: ao receber `corrected_fields`, sobrescrevia `extraction_result.fields`.
- Depois: se `corrected_fields` presente e diferente da versão ativa, cria versão `MANUAL_EDIT` antes de registrar a decisão. A `ValidationDecision` continua sendo criada normalmente (aprovar/rejeitar/corrigir). Nenhuma versão é sobrescrita (FR-013).

---

## Regras transversais

- **Imutabilidade**: nenhuma rota permite editar/excluir uma versão existente (FR-013, FR-016, FR-021).
- **Versão ativa única**: garantida no banco (constraint parcial) e na transação de criação (FR-014).
- **Multi-tenant**: todas as queries filtram pelo tenant do documento.
- **Envelope e mensagens**: respostas no envelope padrão; mensagens de erro humanas e acionáveis (Princípio III).
