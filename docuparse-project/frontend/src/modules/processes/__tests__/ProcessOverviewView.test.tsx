import { MemoryRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../../__tests__/mocks/server'
import { ProcessOverviewView } from '../components/ProcessOverviewView'
import type { ProcessSummary } from '../types'

const OCR = '/api/ocr'

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
    },
]

function renderView() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter>
                <ProcessOverviewView />
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
})
