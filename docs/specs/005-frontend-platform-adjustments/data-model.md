# Data Model: Front-end e Ajustes de Plataforma

**Branch**: `005-frontend-platform-adjustments` | **Date**: 2026-06-15

## Entidades Afetadas

Esta feature não cria novas entidades. Usa apenas entidades existentes.

---

### SchemaConfig (existente — `documents/models.py`)

Utilizada para os modelos padrão de extração criados automaticamente.

| Campo        | Tipo       | Constraint                              | Notas                                  |
|--------------|------------|-----------------------------------------|----------------------------------------|
| `id`         | UUID PK    | auto                                    | —                                      |
| `tenant`     | FK Tenant  | CASCADE                                 | Scoped por tenant                      |
| `schema_id`  | CharField  | UniqueConstraint(tenant+schema_id+ver.) | `nota_fiscal_default`, `conta_agua_default` |
| `version`    | CharField  | UniqueConstraint(tenant+schema_id+ver.) | `v1` para os modelos padrão            |
| `definition` | JSONField  | —                                       | Ver estrutura abaixo                   |
| `is_active`  | Boolean    | default=True                            | —                                      |

**Estrutura do `definition` para modelos padrão**:

```json
{
  "model_name": "NOTA FISCAL DEFAULT",
  "document_type": "nota_fiscal",
  "status": "active",
  "fields": [
    { "name": "campo", "type": "string|decimal|boolean|date", "required": true|false, "rule": "..." }
  ]
}
```

**Idempotência**: Garantida por `get_or_create(tenant, schema_id, version)` — reexecuções não criam duplicatas.

---

### SIMPLE_JWT Settings (configuração, não entidade de banco)

| Setting                 | Antes               | Depois              |
|-------------------------|---------------------|---------------------|
| `ACCESS_TOKEN_LIFETIME` | `timedelta(minutes=15)` | `timedelta(hours=12)` |
| `REFRESH_TOKEN_LIFETIME`| `timedelta(days=7)` | sem alteração       |
| `ROTATE_REFRESH_TOKENS` | `True`              | sem alteração       |
| `BLACKLIST_AFTER_ROTATION` | `True`           | sem alteração       |

---

## Alterações de UI (sem impacto em banco de dados)

| Elemento                     | Antes                | Depois             |
|------------------------------|----------------------|--------------------|
| `SETTINGS_TABS[0].label`     | `'Modelo'`           | `'Documento'`      |
| `SETTINGS_TABS[0].id`        | `'setup'`            | `'ocr'`            |
| `SETTINGS_TABS[1].label`     | `'OCR referencia'`   | `'Modelo'`         |
| `SETTINGS_TABS[1].id`        | `'ocr'`              | `'setup'`          |
| Seção "Vincular layout"      | visível              | removida           |
| `<ReadOnlyTranscription>`    | renderizado          | não renderizado    |
| `<ReadOnlyTranscriptionFormatted>` | renderizado  | sem alteração      |
| `selectedDocument.full_transcription` (dado) | armazenado | sem alteração (continua armazenado) |
