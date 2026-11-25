import { MemoryRouter, useLocation, useNavigationType } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../../../__tests__/mocks/server'
import { ProcessOverviewView } from '../components/ProcessOverviewView'
import type { ProcessSummary } from '../types'

const OCR = '/api/ocr'

// O drawer de verdade depende do layout (contexto do Outlet) e da tela de validação; aqui
// importa só quando ele abre, com qual documento, e o que acontece ao fechar ou validar.
vi.mock('../components/ValidationDrawer', () => ({
    ValidationDrawer: ({
        documentId,
        onClose,
        onValidated,
    }: {
        documentId: string
        onClose: () => void
        onValidated: () => void
    }) => (
        <div role="dialog" aria-label="Validação do documento">
            <span>{`drawer:${documentId}`}</span>
            <button onClick={onClose}>Fechar drawer</button>
            <button onClick={onValidated}>Validar drawer</button>
        </div>
    ),
}))

function Where() {
    const location = useLocation()
    const type = useNavigationType()
    return <output aria-label="rota" data-type={type}>{`${location.pathname}${location.search}`}</output>
}

const ALL: ProcessSummary[] = [
    {
        id: 'a',
        original_filename: 'nota-fiscal.pdf',
        channel: 'manual',
        status: 'VALIDATION_PENDING',
        status_label: 'Aguardando validação',
        received_at: new Date().toISOString(),
        has_error: false,
        current_stage: 'validation_decision',
        last_status_change_at: new Date().toISOString(),
    },
    {
        id: 'b',
        original_filename: 'boleto-condominio.pdf',
        channel: 'manual',
        status: 'RECEIVED',
        status_label: 'Em Fila',
        received_at: new Date().toISOString(),
        has_error: false,
        current_stage: 'register',
        last_status_change_at: new Date().toISOString(),
    },
]

function renderView(initialEntry: string | { pathname: string; search?: string; state?: unknown } = '/') {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={[initialEntry]}>
                <ProcessOverviewView />
                <Where />
            </MemoryRouter>
        </QueryClientProvider>,
    )
}

describe('ProcessOverviewView', () => {
    it('filtra a lista pelo nome do arquivo digitado na busca', async () => {
        server.use(
            http.get(`${OCR}/processes`, ({ request }) => {
                const search = (new URL(request.url).searchParams.get('search') ?? '').toLowerCase()
                const results = search ? ALL.filter((row) => row.original_filename.toLowerCase().includes(search)) : ALL
                return HttpResponse.json({
                    results,
                    count: results.length,
                    page: 1,
                    page_size: 25,
                    total_pages: 1,
                })
            }),
        )
        const user = userEvent.setup()
        renderView()

        expect(await screen.findByText('nota-fiscal.pdf')).toBeInTheDocument()
        expect(screen.getByText('boleto-condominio.pdf')).toBeInTheDocument()

        await user.type(screen.getByPlaceholderText(/nome do arquivo/i), 'boleto')

        await waitFor(() => expect(screen.queryByText('nota-fiscal.pdf')).not.toBeInTheDocument())
        expect(screen.getByText('boleto-condominio.pdf')).toBeInTheDocument()
    })

    it('abre já filtrada pelo status do query param `?status=` (link vindo da Estatísticas)', async () => {
        const seen: (string | null)[] = []
        server.use(
            http.get(`${OCR}/processes`, ({ request }) => {
                const group = new URL(request.url).searchParams.get('status_group')
                seen.push(group)
                const results = group
                    ? ALL.filter((row) => (group === 'erro' ? row.has_error : row.status === 'RECEIVED'))
                    : ALL
                return HttpResponse.json({
                    results,
                    count: results.length,
                    page: 1,
                    page_size: 25,
                    total_pages: 1,
                })
            }),
        )
        renderView('/?status=erro')

        // O request pro backend carrega status_group=erro.
        await waitFor(() => expect(seen).toContain('erro'))
        // E o dropdown reflete o filtro ativo.
        expect(screen.getByRole('combobox')).toHaveValue('erro')
    })

    it('ignora um `?status=` inválido (mostra todos)', async () => {
        const seen: (string | null)[] = []
        server.use(
            http.get(`${OCR}/processes`, ({ request }) => {
                seen.push(new URL(request.url).searchParams.get('status_group'))
                return HttpResponse.json({ results: ALL, count: ALL.length, page: 1, page_size: 25, total_pages: 1 })
            }),
        )
        renderView('/?status=bogus')

        expect(await screen.findByText('nota-fiscal.pdf')).toBeInTheDocument()
        expect(seen.every((g) => g === null)).toBe(true)
        expect(screen.getByRole('combobox')).toHaveValue('')
    })

    describe('drawer de validação aberto por `?validar=<id>`', () => {
        it('não abre o drawer sem o parâmetro', async () => {
            renderView()
            expect(await screen.findByText(/Nenhum processo encontrado/)).toBeInTheDocument()
            expect(screen.queryByRole('dialog', { name: 'Validação do documento' })).not.toBeInTheDocument()
        })

        it('abre o drawer do documento do parâmetro', async () => {
            renderView('/?validar=doc-42')
            const dialog = await screen.findByRole('dialog', { name: 'Validação do documento' })
            expect(dialog).toHaveTextContent('drawer:doc-42')
        })

        it('fechar volta para a tela de origem, quando veio de outra', async () => {
            renderView({ pathname: '/', search: '?validar=doc-42', state: { from: '/payments' } })
            await userEvent.click(await screen.findByRole('button', { name: 'Fechar drawer' }))
            expect(screen.getByLabelText('rota')).toHaveTextContent('/payments')
        })

        it('fechar sem origem só tira o parâmetro e fica na Visão Geral', async () => {
            renderView('/?validar=doc-42')
            await userEvent.click(await screen.findByRole('button', { name: 'Fechar drawer' }))
            expect(screen.getByLabelText('rota')).toHaveTextContent(/^\/$/)
            // Substitui a entrada do histórico: "voltar" não reabre o drawer.
            expect(screen.getByLabelText('rota')).toHaveAttribute('data-type', 'REPLACE')
            expect(screen.queryByRole('dialog', { name: 'Validação do documento' })).not.toBeInTheDocument()
        })

        it('ao validar, atualiza a lista e volta para a origem', async () => {
            let calls = 0
            server.use(
                http.get(`${OCR}/processes`, () => {
                    calls += 1
                    return HttpResponse.json({ results: ALL, count: 2, page: 1, page_size: 25, total_pages: 1 })
                }),
            )
            renderView({ pathname: '/', search: '?validar=doc-42', state: { from: '/payments' } })
            await screen.findByText('nota-fiscal.pdf')
            const before = calls
            await userEvent.click(screen.getByRole('button', { name: 'Validar drawer' }))
            await waitFor(() => expect(screen.getByLabelText('rota')).toHaveTextContent('/payments'))
            expect(calls).toBeGreaterThan(before)
        })
    })
})
