# Contract — Endpoints do catálogo global

Base: `/api/ocr/` (rota de tenant — exige JWT com claim `tenant`, ou token de serviço interno
+ header `X-Tenant`). **URLs e payloads inalterados** em relação a hoje; muda a permissão de
escrita e a semântica (global, não por-tenant).

Auth: `DocuparseAuthentication`. Permissão via `HasDocuparsePermission` (token de serviço
sempre liberado).

| Método + rota | Permissão | Efeito |
|---|---|---|
| `GET /api/ocr/schema-configs` | `models.edit` OU `tenants.manage` | lista todos os `SchemaConfig` do catálogo global |
| `POST /api/ocr/schema-configs` | **`tenants.manage`** | `update_or_create` por `(schema_id, version)` — global |
| `GET /api/ocr/schema-configs/{id}` | `models.edit` OU `tenants.manage` | detalhe |
| `PATCH /api/ocr/schema-configs/{id}` | **`tenants.manage`** | atualização parcial |
| `DELETE /api/ocr/schema-configs/{id}` | **`tenants.manage`** | 403 se `schema_id ∈ PROTECTED_SCHEMA_IDS`; 409 se tiver `LayoutConfig` vinculado (`ProtectedError`); senão 204 |
| `GET /api/ocr/layout-configs` | `models.edit` OU `tenants.manage` | lista `LayoutConfig` (com `schema_config` embed) |
| `POST /api/ocr/layout-configs` | **`tenants.manage`** | cria `LayoutConfig` global; 201 |
| `GET /api/ocr/layout-configs/{id}` | `models.edit` OU `tenants.manage` | detalhe |
| `PATCH /api/ocr/layout-configs/{id}` | **`tenants.manage`** | atualização parcial |

## Mudanças observáveis

1. **Escrita**: um usuário com `models.edit` mas sem `tenants.manage` (papel `tenantAdmin`)
   passa a receber **403** em qualquer POST/PATCH/DELETE do catálogo. Antes: 200/201.
2. **Globalidade**: um `SchemaConfig`/`LayoutConfig` criado enquanto o JWT aponta para o
   tenant A é visível num `GET` feito com JWT do tenant B, imediatamente, sem replicação.
3. **Leitura**: inalterada para quem tem `models.edit`. O pipeline (token de serviço) não é
   afetado.
4. **Payload**: `POST /layout-configs` aceita `tenant_slug` hoje e **ignora** — o campo
   continua sendo ignorado (não vira erro); o frontend para de enviá-lo.

## Formato de resposta

Sem mudança. `GET` de lista retorna array direto (não o envelope `{data,error,meta}` — dívida
pré-existente da constituição §III, **não** endereçada aqui para manter o patch mínimo;
registrar como follow-up).

## Erros

| Situação | HTTP | Corpo |
|---|---|---|
| Sem permissão de escrita | 403 | `{"detail": "..."}` (DRF padrão) |
| DELETE de schema protegido | 403 | `{"detail": "Este modelo é padrão do sistema e não pode ser excluído."}` |
| DELETE de schema com layouts | 409 | `{"detail": "Este modelo possui layouts vinculados e não pode ser excluído."}` |
| `id` inexistente | 404 | `{"detail": "..."}` |
| Sem claim de tenant no JWT | 401/403 | via `JWTTenantMiddleware` (inalterado) |
