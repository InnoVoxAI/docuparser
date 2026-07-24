import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { paginatedDocuments } from './mocks/handlers'
import { ApprovedView } from '../modules/documents'
import { renderWithQueryClient } from './utils'

// US1 / T012-T013 — tela "Aprovados" não tinha nenhum teste de fumaça. Hoje ela
// não é alcançável por navegação real (não está em NAV_ITEMS, nenhum handler
// chama setActiveView('approved')), então este teste renderiza o componente
// diretamente, como já é feito para ValidationView em validation.test.tsx.

function mockApprovedDocuments(documents: Record<string, unknown>[]) {
    server.use(
        http.get('/api/ocr/documents', ({ request }) => HttpResponse.json(paginatedDocuments(documents, request.url))),
    )
}

describe('Aprovados', () => {
    it('lista os documentos aprovados', async () => {
        mockApprovedDocuments([
            {
                id: 'd1',
                status: 'APPROVED',
                original_filename: 'nota-fiscal-aprovada.pdf',
                content_type: 'application/pdf',
                extraction_result: null,
            },
        ])
        renderWithQueryClient(<ApprovedView />)

        expect(await screen.findByText('Documentos aprovados')).toBeInTheDocument()
        expect(await screen.findByText('nota-fiscal-aprovada.pdf')).toBeInTheDocument()
    })

    it('mostra o estado vazio quando não há documentos aprovados', async () => {
        mockApprovedDocuments([])
        renderWithQueryClient(<ApprovedView />)

        expect(await screen.findByText('Nenhum documento aprovado.')).toBeInTheDocument()
    })
})
