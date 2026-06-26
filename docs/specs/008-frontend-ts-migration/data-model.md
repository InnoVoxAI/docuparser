# Phase 1 — Data Model: Tipos do Frontend

Tipos a serem introduzidos no frontend, **espelhando os dados já produzidos pelo backend** (sem alterar contratos — FR-017). Referência: `backend-core/documents/serializers.py` e `users/`. Nenhuma estrutura nova de dados; apenas representação tipada do que já trafega.

## Domínio

### `ExtractionField` / `FieldsMap`
Campo extraído pode vir como objeto ou escalar (formato duplo — edge case da spec).
```ts
interface ExtractionField { value: string; confidence: number | null }
type FieldsMap = Record<string, ExtractionField | string>
```
- Regra: a leitura passa por `parseFieldEntry(raw): { value: string; confidence: number | null }` (type guard — preserva o comportamento atual).

### `ExtractionResult`
```ts
interface ExtractionResult {
  schema_id: string
  schema_version: string
  fields: FieldsMap
  confidence: number
  requires_human_validation: boolean
}
```

### `ExtractionFieldVersion` (feature 007)
```ts
type FieldVersionSource = 'INITIAL_EXTRACTION' | 'PROCESSING' | 'REPROCESSING' | 'MANUAL_EDIT'
interface ExtractionFieldVersion {
  version_number: number
  source_type: FieldVersionSource
  is_active: boolean
  previous_version_number: number | null
  created_at: string
  created_by: string | null
  fields: FieldsMap
}
```

### `DocumentStatus`
```ts
type DocumentStatus =
  | 'RECEIVED' | 'OCR_COMPLETED' | 'OCR_FAILED' | 'LAYOUT_CLASSIFIED'
  | 'EXTRACTION_COMPLETED' | 'VALIDATION_PENDING' | 'APPROVED' | 'REJECTED'
  | 'ERP_INTEGRATION_REQUESTED' | 'ERP_SENT' | 'ERP_FAILED'
```

### `Document`
```ts
interface Document {
  id: string
  status: DocumentStatus
  channel: string
  original_filename: string
  content_type: string
  document_type?: string
  layout?: string
  received_at?: string
  updated_at?: string
  metadata?: Record<string, unknown>
  metadata_channel?: Record<string, unknown> | null
  extraction_result: ExtractionResult | null
  active_field_version_number: number | null   // DocumentDetailSerializer (feature 007)
  full_transcription?: string
  full_transcription_formatted?: string
  // campos adicionais do DocumentListSerializer/DetailSerializer (rejection_notes, decision_date, etc.) tipados conforme uso
}
```

### Configuração / domínio auxiliar
- `SchemaConfig`, `LayoutConfig`, `OCRSettings`, `EmailSettings`, `IntegrationSettings` — tipados conforme os respectivos serializers e o uso real em `SettingsView`.
- `SchemaField` — forma dos itens em `*_DEFAULT_FIELDS` (em `src/models/**`).

## Autenticação / Permissões

```ts
interface User { id: string; name?: string; email: string; permissions: string[] }

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (code: string) => boolean
}
```
- `useAuth()` retorna `AuthContextValue` (garantir não-nulo lançando erro se usado fora do provider).
- Permissões usadas hoje (de `NAV_ITEMS`): `documents.send`, `inbox.view`, `documents.validate`, `operations.access`, `roles.manage`, `users.manage`.

## Estado de UI (local)

```ts
interface FieldRow { name: string; value: string; confidence: number | null }
interface SaveMessage { tone: 'success' | 'error' | 'neutral'; text: string }
type ActiveView = 'upload' | 'inbox' | 'dashboard' | 'validation'
  | 'operations' | 'settings' | 'users' | 'roles'
```
- `useState` deve receber tipo quando o inicial não revela (ex.: `useState<Document | null>(null)`, `useState<FieldRow[]>([])`). Primitivos (`''`, `false`) ficam inferidos.

## DTOs de integração (request/response)

Aplicados via generics do axios, sem mudar payloads:
- `api.get<Document[]>('/documents')`, `api.get<Document>('/documents/{id}')`
- `api.post<ExtractionResult>('/documents/{id}/langextract', { schema_config_id })`
- `api.put<ExtractionFieldVersion>('/documents/{id}/fields', { base_version_number, fields: {name,value}[] })`
- `api.get<{ results: ExtractionFieldVersion[]; count: number; active_version_number: number | null }>('/documents/{id}/field-versions')`
- `authApi.post<{ access: string; refresh: string; user: User }>('/login', …)`, `authApi.get<User>('/me')`
- Settings/usuários/roles conforme `SettingsView`/`GerenciarUsuarios`/`GerenciarRoles`.

## Variáveis de ambiente

```ts
interface ImportMetaEnv {
  readonly VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN?: string
  readonly VITE_BACKEND_CORE_URL?: string
  readonly VITE_BACKEND_COM_URL?: string
}
```
- Opcionais (`?`) — ausência não pode quebrar build/runtime (edge case da spec).
