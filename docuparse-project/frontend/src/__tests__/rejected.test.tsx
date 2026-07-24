import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { paginatedDocuments } from './mocks/handlers'
import { RejectedView } from '../main'

// US1 / T012-T013 — tela "Rejeitados" (listagem completa, distinta do modal de
// documento rejeitado já coberto em flows.test.tsx) não tinha teste de fumaça
// próprio e, como Aprovados, não é alcançável por navegação real hoje (não
// está em NAV_ITEMS, nenhum handler chama setActiveView('rejected')).

function mockRejectedDocuments(documents: Record<string, unknown>[]) {
    server.use(
        http.get('/api/ocr/documents', ({ request }) => HttpResponse.json(paginatedDocuments(documents, request.url))),
    )
}

function renderRejected() {
    return render(<RejectedView onReprocess={vi.fn()} onDelete={vi.fn()} onRefresh={vi.fn()} />)
}

describe('Rejeitados', () => {
    it('lista os documentos rejeitados com o motivo', async () => {
        mockRejectedDocuments([
            {
                id: 'd1',
                status: 'REJECTED',
                original_filename: 'boleto-rejeitado.pdf',
                content_type: 'application/pdf',
                rejection_notes: 'Valor divergente',
            },
        ])
        renderRejected()

        expect(await screen.findByText('Documentos rejeitados')).toBeInTheDocument()
        expect(await screen.findByText('boleto-rejeitado.pdf')).toBeInTheDocument()

        const user = userEvent.setup()
        await user.click(screen.getByRole('button', { name: /Visualizar Motivo/i }))
        expect(await screen.findByText('Valor divergente')).toBeInTheDocument()
    })

    it('mostra o estado vazio quando não há documentos rejeitados', async () => {
        mockRejectedDocuments([])
        renderRejected()

        expect(await screen.findByText('Nenhum documento rejeitado.')).toBeInTheDocument()
    })
})
