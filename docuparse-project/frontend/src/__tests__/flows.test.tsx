import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { paginatedDocuments } from './mocks/handlers'
import { renderApp } from './utils'

// US1 / T019 — integração de Inbox / Dashboard (rejeitados) / Operações (DLQ) /
// Configurações, dirigida pela árvore real da aplicação com MSW.

const ALL_PERMISSIONS = [
  'documents.send',
  'inbox.view',
  'documents.validate',
  'operations.access',
  'roles.manage',
  'users.manage',
]

function mockSession(documents: unknown[] = []) {
  server.use(
    http.get('/api/auth/me', () =>
      HttpResponse.json({ id: 'u1', name: 'Admin', email: 'admin@docuparse.local', permissions: ALL_PERMISSIONS }),
    ),
    http.get('/api/ocr/documents', ({ request }) => HttpResponse.json(paginatedDocuments(documents as Record<string, unknown>[], request.url))),
    http.get('/api/ocr/schema-configs', () => HttpResponse.json([])),
    http.get('/api/ocr/layout-configs', () => HttpResponse.json([])),
  )
}

function doc(overrides: Record<string, unknown>) {
  return {
    id: 'd1',
    status: 'RECEIVED',
    channel: 'manual',
    original_filename: 'documento.pdf',
    content_type: 'application/pdf',
    extraction_result: null,
    active_field_version_number: null,
    ...overrides,
  }
}

async function navigate(label: string) {
  const user = userEvent.setup()
  renderApp()
  await user.click((await screen.findAllByText(label))[0])
  return user
}

beforeEach(() => localStorage.setItem('access_token', 'tok'))

describe('Inbox', () => {
  it('lista documentos pendentes e filtra pela busca', async () => {
    mockSession([
      doc({ id: 'd1', original_filename: 'nota-fiscal.pdf', status: 'RECEIVED' }),
      doc({ id: 'd2', original_filename: 'boleto-condominio.pdf', status: 'EXTRACTION_COMPLETED' }),
    ])
    const user = await navigate('Inbox')

    expect(await screen.findByText('nota-fiscal.pdf')).toBeInTheDocument()
    expect(screen.getByText('boleto-condominio.pdf')).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText(/Buscar por nome/i), 'boleto')
    expect(screen.queryByText('nota-fiscal.pdf')).not.toBeInTheDocument()
    expect(screen.getByText('boleto-condominio.pdf')).toBeInTheDocument()
  })
})

describe('Dashboard — documento rejeitado', () => {
  it('abre o modal de rejeição e dispara reprocessamento', async () => {
    let reprocessCalled = false
    server.use(
      http.post('/api/ocr/documents/:id/reprocess-ocr', () => {
        reprocessCalled = true
        return HttpResponse.json({ ok: true })
      }),
    )
    mockSession([
      doc({ id: 'dR', original_filename: 'rejeitado.pdf', status: 'REJECTED', rejection_notes: 'Documento ilegível' }),
    ])
    const user = await navigate('Dashboard')

    await user.click(await screen.findByText('rejeitado.pdf'))
    // Modal de documento rejeitado
    expect(await screen.findByText('Documento Rejeitado')).toBeInTheDocument()
    expect(screen.getByText('Documento ilegível')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Reprocessar/i }))
    await waitFor(() => expect(reprocessCalled).toBe(true))
  })
})

describe('Operações (DLQ)', () => {
  it('mostra streams e detalha um evento ao selecioná-lo', async () => {
    mockSession([])
    server.use(
      http.get('/api/ocr/operations/dlq/summary', () =>
        HttpResponse.json({ total: 1, streams: [{ stream: 'ocr.completed.dlq', count: 1 }] }),
      ),
      http.get('/api/ocr/operations/dlq/events', () =>
        HttpResponse.json({
          entries: [
            { id: 'e1', source: 'worker-ocr', event_type: 'ocr.completed', event_id: 'evt-1', error_type: 'TimeoutError', error: 'deadline exceeded', original_stream: 'ocr.completed', payload: { foo: 'bar' } },
          ],
        }),
      ),
    )
    const user = await navigate('Operacoes')

    expect(await screen.findByText('TimeoutError')).toBeInTheDocument()
    await user.click(screen.getByText('worker-ocr'))
    // Painel de detalhe abre com a ação de reenfileiramento.
    expect(await screen.findByRole('button', { name: /Reenfileirar/i })).toBeInTheDocument()
    expect((await screen.findAllByText('deadline exceeded')).length).toBeGreaterThan(0)
  })
})

describe('Configurações', () => {
  it('renderiza a tela de configurações com as áreas disponíveis', async () => {
    mockSession([])
    await navigate('Configuracoes')
    // A tela de configurações expõe as áreas/abas de setup.
    expect((await screen.findAllByText(/OCR/i)).length).toBeGreaterThan(0)
  })
})

describe('Configurações — áreas e salvamento', () => {
  it('navega entre OCR/Email/Integrações e dispara os respectivos saves', async () => {
    const patched: string[] = []
    server.use(
      http.get('/api/ocr/settings/ocr', () => HttpResponse.json({})),
      http.get('/api/ocr/settings/email', () => HttpResponse.json({})),
      http.get('/api/ocr/settings/integrations', () => HttpResponse.json({})),
      http.patch('/api/ocr/settings/ocr', () => { patched.push('ocr'); return HttpResponse.json({}) }),
      http.patch('/api/ocr/settings/email', () => { patched.push('email'); return HttpResponse.json({}) }),
      http.patch('/api/ocr/settings/integrations', () => { patched.push('integrations'); return HttpResponse.json({}) }),
    )
    mockSession([])
    const user = await navigate('Configuracoes')

    await user.click((await screen.findAllByText('OCR'))[0])
    await user.click(await screen.findByRole('button', { name: /Salvar OCR/i }))
    await waitFor(() => expect(patched).toContain('ocr'))

    await user.click((await screen.findAllByText('Email'))[0])
    await user.click(await screen.findByRole('button', { name: /Salvar email/i }))
    await waitFor(() => expect(patched).toContain('email'))

    await user.click((await screen.findAllByText('Integracoes'))[0])
    await user.click(await screen.findByRole('button', { name: /Salvar integracoes/i }))
    await waitFor(() => expect(patched).toContain('integrations'))
  })
})

describe('Usuários (CRUD)', () => {
  it('lista usuários e cria um novo via modal', async () => {
    let created = false
    server.use(
      http.get('/api/ocr/users', () =>
        HttpResponse.json([{ id: 'u9', name: 'Maria', email: 'maria@docuparse.local', role: { id: 'r1', name: 'Operador' }, is_active: true }]),
      ),
      http.get('/api/ocr/roles', () => HttpResponse.json([{ id: 'r1', name: 'Operador' }])),
      http.post('/api/ocr/users', () => {
        created = true
        return HttpResponse.json({ id: 'u10' }, { status: 201 })
      }),
    )
    mockSession([])
    const user = await navigate('Usuários')

    expect(await screen.findByText('Maria')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Novo Usuário/i }))
    expect(await screen.findByRole('heading', { name: /Novo Usuário/i })).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('Nome'), 'João')
    await user.type(screen.getByPlaceholderText('E-mail'), 'joao@docuparse.local')
    await user.type(screen.getByPlaceholderText(/Senha/i), 'segredo123')
    await user.selectOptions(screen.getByRole('combobox'), 'r1')
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }))

    await waitFor(() => expect(created).toBe(true))
  })
})

describe('Roles (CRUD)', () => {
  it('lista roles e cria uma nova com permissões', async () => {
    let created = false
    server.use(
      http.get('/api/ocr/roles', () =>
        HttpResponse.json([{ id: 'r1', name: 'Operador', permissions: [], users_count: 2 }]),
      ),
      http.get('/api/ocr/permissions', () =>
        HttpResponse.json([
          { code: 'inbox.view', description: 'Ver inbox' },
          { code: 'documents.validate', description: 'Validar documentos' },
        ]),
      ),
      http.post('/api/ocr/roles', () => {
        created = true
        return HttpResponse.json({ id: 'r2' }, { status: 201 })
      }),
    )
    mockSession([])
    const user = await navigate('Roles')

    expect(await screen.findByText('Operador')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Nova Role/i }))
    expect(await screen.findByRole('heading', { name: /Nova Role/i })).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText(/Nome da role/i), 'Auditor')
    await user.click(screen.getByText('Ver inbox')) // marca a permissão
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }))

    await waitFor(() => expect(created).toBe(true))
  })
})

describe('Upload', () => {
  it('envia um documento manual e mostra a confirmação', async () => {
    // jsdom não implementa object URLs usados pelo preview do upload.
    ;(URL as unknown as { createObjectURL: () => string }).createObjectURL = vi.fn(() => 'blob:x')
    ;(URL as unknown as { revokeObjectURL: () => void }).revokeObjectURL = vi.fn()
    server.use(
      http.post('/com/api/v1/documents/manual', () => HttpResponse.json({ document_id: 'doc-123' })),
    )
    mockSession([])
    const user = await navigate('Upload')

    const file = new File(['conteudo'], 'nota.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText('Arquivo'), file)
    await user.click(screen.getByRole('button', { name: /^Enviar$/i }))

    expect(await screen.findByText(/Documento recebido: doc-123/i)).toBeInTheDocument()
  })
})

describe('Visualização do documento (ação de olho)', () => {
  it('mantém as informações existentes e adiciona a pré-visualização do documento', async () => {
    ;(URL as unknown as { createObjectURL: () => string }).createObjectURL = vi.fn(() => 'blob:preview')
    ;(URL as unknown as { revokeObjectURL: () => void }).revokeObjectURL = vi.fn()
    let fileRequested = ''
    server.use(
      http.get('/api/ocr/documents/:id/file', ({ params }) => {
        fileRequested = String(params.id)
        return new HttpResponse(new Blob(['%PDF']), { headers: { 'Content-Type': 'application/pdf' } })
      }),
    )
    mockSession([doc({ id: 'd1', original_filename: 'nota-fiscal.pdf', status: 'RECEIVED', content_type: 'application/pdf' })])
    const user = await navigate('Inbox')

    await screen.findByText('nota-fiscal.pdf')
    await user.click(screen.getByRole('button', { name: /Ver informações do documento/i }))

    // Informações já existentes permanecem (FR-012/FR-019).
    expect(await screen.findByText('Informações do documento')).toBeInTheDocument()
    expect(screen.getByText('Código de Processo')).toBeInTheDocument()
    expect(screen.getByText('Documento original')).toBeInTheDocument()

    // Pré-visualização inline do documento correto, sem download (blob → object URL).
    await waitFor(() => expect(screen.getByTitle(/Documento nota-fiscal\.pdf/i)).toBeInTheDocument())
    expect(fileRequested).toBe('d1')
    expect(URL.createObjectURL).toHaveBeenCalled()
  })

  it('exibe estado de erro quando o arquivo não carrega', async () => {
    ;(URL as unknown as { createObjectURL: () => string }).createObjectURL = vi.fn(() => 'blob:preview')
    ;(URL as unknown as { revokeObjectURL: () => void }).revokeObjectURL = vi.fn()
    server.use(
      http.get('/api/ocr/documents/:id/file', () => new HttpResponse(null, { status: 404 })),
    )
    mockSession([doc({ id: 'd1', original_filename: 'nota-fiscal.pdf', status: 'RECEIVED', content_type: 'application/pdf' })])
    const user = await navigate('Inbox')

    await screen.findByText('nota-fiscal.pdf')
    await user.click(screen.getByRole('button', { name: /Ver informações do documento/i }))

    expect(await screen.findByText('Informações do documento')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/Nao foi possivel carregar a pre-visualizacao/i)).toBeInTheDocument())
  })
})
