import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../../__tests__/mocks/server'
import { renderWithQueryClient } from '../../../__tests__/utils'
import { ProcessTable } from '../components/ProcessTable'
import type { ProcessSummary } from '../types'

const OCR = '/api/ocr'

function process(overrides: Partial<ProcessSummary> = {}): ProcessSummary {
    return {
        id: 'd1',
        original_filename: 'nota-fiscal.pdf',
        channel: 'manual',
        status: 'VALIDATION_PENDING',
        status_label: 'Aguardando validação',
        received_at: new Date().toISOString(),
        has_error: false,
        current_stage: 'validation_decision',
        last_status_change_at: new Date().toISOString(),
        ...overrides,
    }
}

describe('ProcessTable', () => {
    it('mostra nome, status de negócio e última atualização de cada processo', () => {
        renderWithQueryClient(<ProcessTable processes={[process({ last_status_change_at: '2026-03-05T14:30:00Z' })]} />)
        expect(screen.getByText('nota-fiscal.pdf')).toBeInTheDocument()
        expect(screen.getByText('Aguardando validação')).toBeInTheDocument()
        expect(screen.getByText('Última atualização')).toBeInTheDocument()
        // "Última atualização" não pode ficar vazia/traço quando o backend manda um valor.
        expect(screen.queryByText('-')).not.toBeInTheDocument()
    })

    it('exibe "-" quando o processo não tem última atualização', () => {
        renderWithQueryClient(<ProcessTable processes={[process({ last_status_change_at: null })]} />)
        expect(screen.getByText('-')).toBeInTheDocument()
    })

    it('expande a linha e mostra as 4 caixas do processo', async () => {
        server.use(
            http.get(`${OCR}/documents/:id/pipeline`, ({ params }) =>
                HttpResponse.json({
                    document_id: params.id,
                    original_filename: 'nota-fiscal.pdf',
                    steps: [
                        { key: 'register', label: 'Registro', status: 'OK', retryable: false, executions: [] },
                        { key: 'ocr', label: 'OCR', status: 'OK', retryable: true, executions: [] },
                        { key: 'extraction', label: 'Extração', status: 'OK', retryable: true, executions: [] },
                        {
                            key: 'validation_decision',
                            label: 'Validação',
                            status: 'PENDING',
                            retryable: false,
                            executions: [],
                        },
                        {
                            key: 'classification',
                            label: 'Classificação',
                            status: 'PENDING',
                            retryable: false,
                            executions: [],
                        },
                    ],
                }),
            ),
        )
        const user = userEvent.setup()
        renderWithQueryClient(<ProcessTable processes={[process()]} />)

        await user.click(screen.getByRole('button', { name: /nota-fiscal\.pdf/ }))

        expect(await screen.findByText('Em fila')).toBeInTheDocument()
        expect(screen.getByText('Ingestão')).toBeInTheDocument()
        // "Validação" aguardando decisão → vira botão clicável.
        await waitFor(() => expect(screen.getByRole('button', { name: /Validação/ })).toBeInTheDocument())
        expect(screen.getByText('Classificação')).toBeInTheDocument()
    })
})
