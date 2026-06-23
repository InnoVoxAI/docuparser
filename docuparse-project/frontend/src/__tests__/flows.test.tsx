import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
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
    http.get('/api/ocr/documents', () => HttpResponse.json(documents)),
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
