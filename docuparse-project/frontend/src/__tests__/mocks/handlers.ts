import { http, HttpResponse } from 'msw'

// Handlers MSW espelhando os endpoints existentes (ver
// docs/specs/008-frontend-ts-migration/contracts/frontend-types-and-test-surface.md).
// Estes são stubs iniciais (scaffolding). Cada teste pode sobrescrever um handler
// com server.use(...) para cenários específicos (ex.: 409 de conflito de versão).
//
// O frontend chama caminhos relativos (proxy do Vite): /api/ocr/*, /api/auth/*, /com/*.

const OCR = '/api/ocr'
const AUTH = '/api/auth'

interface DocLike {
  status?: string
  original_filename?: string
  document_type?: string
  channel?: string
  [key: string]: unknown
}

/**
 * Constrói o envelope paginado de `GET /documents` (feature 009) a partir de um
 * conjunto fixo, honrando `page`/`page_size`/`status` (CSV)/`search` da URL —
 * espelha o backend para os testes de paginação/busca server-side.
 */
export function paginatedDocuments(all: DocLike[], url: string) {
  const params = new URL(url).searchParams
  const page = Math.max(parseInt(params.get('page') ?? '1', 10) || 1, 1)
  const pageSize = Math.min(Math.max(parseInt(params.get('page_size') ?? '25', 10) || 25, 1), 25)
  const status = params.get('status')
  const search = (params.get('search') ?? '').trim().toLowerCase()

  let filtered = all
  if (status) {
    const statuses = status.split(',').map((s) => s.trim()).filter(Boolean)
    filtered = filtered.filter((d) => statuses.includes(String(d.status)))
  }
  if (search) {
    filtered = filtered.filter((d) =>
      [d.original_filename, d.status, d.document_type, d.channel].some((v) =>
        String(v ?? '').toLowerCase().includes(search),
      ),
    )
  }
  const count = filtered.length
  const total_pages = count ? Math.ceil(count / pageSize) : 0
  const start = (page - 1) * pageSize
  return {
    results: filtered.slice(start, start + pageSize),
    count,
    page,
    page_size: pageSize,
    total_pages,
  }
}

export const handlers = [
  // --- Auth ---
  http.post(`${AUTH}/login`, async () => {
    return HttpResponse.json({
      access: 'test-access',
      refresh: 'test-refresh',
      user: { id: 'u1', name: 'Operador', email: 'op@docuparse.local', permissions: ['inbox.view', 'documents.validate'] },
    })
  }),
  http.get(`${AUTH}/me`, () => {
    return HttpResponse.json({ id: 'u1', name: 'Operador', email: 'op@docuparse.local', permissions: ['inbox.view', 'documents.validate'] })
  }),
  http.post(`${AUTH}/logout`, () => new HttpResponse(null, { status: 204 })),

  // --- Documentos ---
  http.get(`${OCR}/documents`, ({ request }) => HttpResponse.json(paginatedDocuments([], request.url))),
  http.get(`${OCR}/schema-configs`, () => HttpResponse.json([])),
  http.get(`${OCR}/layout-configs`, () => HttpResponse.json([])),
  http.get(`${OCR}/documents/:id`, ({ params }) =>
    HttpResponse.json({
      id: params.id,
      status: 'EXTRACTION_COMPLETED',
      channel: 'manual',
      original_filename: 'doc.pdf',
      content_type: 'application/pdf',
      extraction_result: { schema_id: 's', schema_version: 'v1', fields: {}, confidence: 0.9, requires_human_validation: true },
      active_field_version_number: 1,
    }),
  ),

  // --- Campos / versões (feature 007) ---
  http.put(`${OCR}/documents/:id/fields`, () =>
    HttpResponse.json(
      {
        version_number: 2,
        source_type: 'MANUAL_EDIT',
        is_active: true,
        previous_version_number: 1,
        created_at: new Date().toISOString(),
        created_by: 'op@docuparse.local',
        fields: {},
      },
      { status: 201 },
    ),
  ),
  http.get(`${OCR}/documents/:id/field-versions`, () =>
    HttpResponse.json({ results: [], count: 0, active_version_number: 1 }),
  ),

  // --- Validação / classificação ---
  http.post(`${OCR}/classify-text`, () => HttpResponse.json({ schema_id: null })),
  http.post(`${OCR}/documents/:id/validate`, () => HttpResponse.json({ id: 'v1', decision: 'approved' }, { status: 201 })),
]
