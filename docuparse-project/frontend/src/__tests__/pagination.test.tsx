import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { paginatedDocuments } from './mocks/handlers'
import { renderApp } from './utils'

// US1 / T006 — controles de paginação server-side (navegação, posição, reset ao
// buscar, limites desabilitados), exercitados pela tela Inbox real com MSW.

const ALL_PERMISSIONS = ['documents.send', 'inbox.view', 'documents.validate', 'operations.access', 'roles.manage', 'users.manage']

function mockSession(documents: Record<string, unknown>[]) {
  server.use(
    http.get('/api/auth/me', () =>
      HttpResponse.json({ id: 'u1', name: 'Admin', email: 'admin@docuparse.local', permissions: ALL_PERMISSIONS }),
    ),
    http.get('/api/ocr/documents', ({ request }) => HttpResponse.json(paginatedDocuments(documents, request.url))),
    http.get('/api/ocr/schema-configs', () => HttpResponse.json([])),
    http.get('/api/ocr/layout-configs', () => HttpResponse.json([])),
  )
}

function makeDocs(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `d${i}`,
    status: 'RECEIVED',
    channel: 'manual',
    original_filename: `doc-${String(i).padStart(3, '0')}.pdf`,
    content_type: 'application/pdf',
    extraction_result: null,
    active_field_version_number: null,
  }))
}

async function openInbox() {
  const user = userEvent.setup()
  renderApp()
  await user.click((await screen.findAllByText('Inbox'))[0])
  return user
}

beforeEach(() => localStorage.setItem('access_token', 'tok'))

describe('Paginação (Inbox)', () => {
  it('exibe no máximo 25 itens e a posição da página com o total', async () => {
    mockSession(makeDocs(30))
    await openInbox()

    expect(await screen.findByText('doc-000.pdf')).toBeInTheDocument()
    expect(screen.getByText('doc-024.pdf')).toBeInTheDocument()
    expect(screen.queryByText('doc-025.pdf')).not.toBeInTheDocument()
    expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument()
    expect(screen.getByText(/Mostrando 1.*25 de 30/)).toBeInTheDocument()
  })

  it('navega entre páginas e desabilita os botões nos limites', async () => {
    mockSession(makeDocs(30))
    const user = await openInbox()
    await screen.findByText('doc-000.pdf')

    const prev = screen.getByRole('button', { name: /Página anterior/i })
    const next = screen.getByRole('button', { name: /Próxima página/i })
    expect(prev).toBeDisabled()
    expect(next).toBeEnabled()

    await user.click(next)

    expect(await screen.findByText('doc-025.pdf')).toBeInTheDocument()
    expect(screen.queryByText('doc-000.pdf')).not.toBeInTheDocument()
    expect(screen.getByText(/Página 2 de 2/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Próxima página/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Página anterior/i })).toBeEnabled()
  })

  it('reinicia na página 1 ao buscar, filtrando sobre todo o conjunto', async () => {
    mockSession(makeDocs(30))
    const user = await openInbox()
    await screen.findByText('doc-000.pdf')

    // vai para a página 2
    await user.click(screen.getByRole('button', { name: /Próxima página/i }))
    expect(await screen.findByText('doc-025.pdf')).toBeInTheDocument()

    // busca por um item que está fora da página atual → reinicia em 1
    const input = screen.getByPlaceholderText(/Buscar/i)
    await user.type(input, 'doc-029')

    await waitFor(() => expect(screen.getByText('doc-029.pdf')).toBeInTheDocument())
    expect(screen.getByText(/Página 1 de 1/)).toBeInTheDocument()
    expect(screen.getByText(/Mostrando 1.*1 de 1/)).toBeInTheDocument()
  })
})
