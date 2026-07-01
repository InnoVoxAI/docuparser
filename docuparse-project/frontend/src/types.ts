// Tipos do domínio do frontend DocuParse.
//
// Espelham os dados já produzidos pelo backend (serializers de `documents/` e
// `users/`) — nenhuma estrutura nova de dados, apenas a representação tipada do
// que já trafega hoje (FR-017). Referência: docs/specs/008-frontend-ts-migration/data-model.md

// =========================================================
// Campos extraídos
// =========================================================

/** Campo extraído no formato objeto. */
export interface ExtractionField {
  value: string
  confidence: number | null
}

/**
 * Mapa de campos extraídos. Um campo pode vir como objeto `{ value, confidence }`
 * ou como escalar (formato duplo — edge case preservado da spec). A leitura passa
 * por `parseFieldEntry` (type guard) para normalizar.
 */
export type FieldsMap = Record<string, ExtractionField | string>

export interface ExtractionResult {
  schema_id: string
  schema_version: string
  fields: FieldsMap
  confidence: number
  requires_human_validation: boolean
  // Preenchido quando a extração é processada de forma assíncrona pelo backend;
  // usado pelo polling do frontend para detectar quando um novo resultado chegou.
  updated_at?: string
}

// =========================================================
// Versionamento de campos (feature 007)
// =========================================================

export type FieldVersionSource =
  | 'INITIAL_EXTRACTION'
  | 'PROCESSING'
  | 'REPROCESSING'
  | 'MANUAL_EDIT'

export interface ExtractionFieldVersion {
  version_number: number
  source_type: FieldVersionSource
  is_active: boolean
  previous_version_number: number | null
  created_at: string
  created_by: string | null
  fields: FieldsMap
}

/** Resposta de `GET /documents/{id}/field-versions`. */
export interface FieldVersionsResponse {
  results: ExtractionFieldVersion[]
  count: number
  active_version_number: number | null
}

// =========================================================
// Documento
// =========================================================

export type DocumentStatus =
  | 'RECEIVED'
  | 'OCR_COMPLETED'
  | 'OCR_FAILED'
  | 'LAYOUT_CLASSIFIED'
  | 'EXTRACTION_COMPLETED'
  | 'VALIDATION_PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'ERP_INTEGRATION_REQUESTED'
  | 'ERP_SENT'
  | 'ERP_FAILED'

export interface Document {
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
  active_field_version_number: number | null
  full_transcription?: string
  full_transcription_formatted?: string
  rejection_notes?: string | null
  decision_date?: string | null
  approved_at?: string | null
  rejected_at?: string | null
  // Campos adicionais do List/DetailSerializer são tolerados conforme uso.
  [key: string]: unknown
}

// =========================================================
// Paginação (feature 009)
// =========================================================

/** Envelope paginado genérico (espelha o backend `documents/pagination.py`). */
export interface Paginated<T> {
  results: T[]
  count: number
  page: number
  page_size: number
  total_pages: number
}

/** Parâmetros de uma requisição de listagem paginada de documentos. */
export interface DocumentListParams {
  page: number
  page_size?: number // default 25 (cap 25)
  status?: string // single ou CSV (buckets por tela)
  search?: string
  tenant?: string
}

// =========================================================
// Modelos documentais (src/models/**)
// =========================================================

/** Forma dos itens em `*_DEFAULT_FIELDS`. */
export interface SchemaField {
  name: string
  type: string
  required: boolean
  rule: string
}

/** Forma dos itens em `*_DEFAULT_EXAMPLES`. */
export interface SchemaExample {
  field: string
  expected: string
  source: string
}

/** Conjunto de regras de pós-processamento (`*_DEFAULT_RULES`) — heterogêneo. */
export type SchemaRules = Record<string, unknown>

/**
 * Configuração de schema vinda do backend (`SchemaConfigSerializer`). A forma
 * exata varia entre endpoints; mantemos os campos consumidos pela UI e um índice
 * permissivo para o restante (sem alterar contrato).
 */
export interface SchemaConfig {
  id: string
  schema_id?: string
  name?: string
  schema_version?: string
  [key: string]: any
}

/** Configuração de layout vinda do backend (`LayoutConfigSerializer`). */
export interface LayoutConfig {
  id: string
  name?: string
  [key: string]: any
}

// =========================================================
// Autenticação / Permissões
// =========================================================

export interface User {
  id: string
  name?: string
  email: string
  permissions: string[]
}

export interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (code: string) => boolean
}

/** Resposta de `POST /login`. */
export interface LoginResponse {
  access: string
  refresh: string
  user: User
}

// =========================================================
// Estado de UI (local)
// =========================================================

export interface FieldRow {
  name: string
  value: string
  confidence: number | null
}

export interface SaveMessage {
  tone: 'success' | 'error' | 'neutral'
  text: string
}

export type ActiveView =
  | 'upload'
  | 'inbox'
  | 'dashboard'
  | 'validation'
  | 'approved'
  | 'rejected'
  | 'operations'
  | 'settings'
  | 'users'
  | 'roles'
