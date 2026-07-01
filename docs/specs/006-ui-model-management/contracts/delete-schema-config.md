# Contract: Delete SchemaConfig

**Endpoint**: `DELETE /schema-configs/<uuid:schema_id>`

**Auth**: Internal token required (same as existing GET/PATCH)

---

## Request

```
DELETE /api/schema-configs/{id}
Authorization: <internal-token>
```

No request body.

---

## Responses

### 204 No Content — Exclusão bem-sucedida

```
HTTP/1.1 204 No Content
```

Body: empty

---

### 403 Forbidden — Modelo padrão protegido

```json
{
  "detail": "Este modelo é padrão do sistema e não pode ser excluído."
}
```

Triggered when `schema.schema_id` in `["nota_fiscal_default", "conta_agua_default"]`.

---

### 409 Conflict — Modelo com layouts vinculados

```json
{
  "detail": "Este modelo possui layouts vinculados e não pode ser excluído."
}
```

Triggered when `LayoutConfig` records reference this `SchemaConfig` (`on_delete=PROTECT`).

---

### 404 Not Found — ID não encontrado

```json
{
  "detail": "Not found."
}
```

---

## Frontend Usage

```js
// Check protection before calling API
const PROTECTED_SCHEMA_IDS = ['nota_fiscal_default', 'conta_agua_default']

async function deleteSchema(schema) {
    if (PROTECTED_SCHEMA_IDS.includes(schema.schema_id)) {
        // Show inline message — do NOT call API
        return
    }
    await api.delete(`/schema-configs/${schema.id}`)
    // Refresh schemas list on success
}
```
