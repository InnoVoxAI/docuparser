import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { ValidationView } from '../modules/documents'
import type { Document } from '../types'
import { renderWithQueryClient } from './utils'

// US1 / T018 — fluxo de Validação (feature 007: salvar campos / conflito 409 / histórico).
const docId = 'doc-1'
const baseDoc: Document = {
    id: docId,
    status: 'EXTRACTION_COMPLETED',
    channel: 'manual',
    original_filename: 'nota.pdf',
    content_type: 'application/pdf',
    active_field_version_number: 1,
    extraction_result: {
        schema_id: 's',
        schema_version: 'v1',
        fields: { valor: { value: '100', confidence: 0.8 } },
        confidence: 0.8,
        requires_human_validation: true,
    },
}

function renderValidation() {
    return renderWithQueryClient(
        <ValidationView
            schemas={[]}
            selectedDocument={baseDoc}
            selectedDocumentId={docId}
            onValidated={vi.fn()}
            onBackToInbox={vi.fn()}
        />,
    )
}

describe('Validação — salvar campos e histórico', () => {
    it('exibe os campos extraídos da versão ativa', async () => {
        renderValidation()
        expect(await screen.findByDisplayValue('100')).toBeInTheDocument()
    })

    it('esconde Salvar Alterações/Visualizar Histórico até haver edição não salva', async () => {
        renderValidation()
        await screen.findByDisplayValue('100')

        expect(screen.queryByRole('button', { name: /Salvar Alterações/i })).not.toBeInTheDocument()
        expect(screen.queryByRole('button', { name: /Visualizar Histórico/i })).not.toBeInTheDocument()
    })

    it('salva alterações com confirmação e cria nova versão (201)', async () => {
        const user = userEvent.setup()
        renderValidation()
        await user.type(await screen.findByDisplayValue('100'), '5')

        await user.click(screen.getByRole('button', { name: /Salvar Alterações/i }))
        // diálogo de confirmação
        await user.click(screen.getByRole('button', { name: /^Salvar$/i }))

        expect(await screen.findByText(/Versão 2 salva com sucesso/i)).toBeInTheDocument()
    })

    it('bloqueia e avisa em caso de conflito de versão (409)', async () => {
        server.use(
            http.put(`/api/ocr/documents/${docId}/fields`, () =>
                HttpResponse.json({ detail: 'conflito', active_version_number: 5 }, { status: 409 }),
            ),
        )
        const user = userEvent.setup()
        renderValidation()
        await user.type(await screen.findByDisplayValue('100'), '5')

        await user.click(screen.getByRole('button', { name: /Salvar Alterações/i }))
        await user.click(screen.getByRole('button', { name: /^Salvar$/i }))

        expect(await screen.findByText(/atualizada por outro processo/i)).toBeInTheDocument()
    })

    it('aprova o documento e volta para o inbox', async () => {
        const user = userEvent.setup()
        const onValidated = vi.fn()
        const onBackToInbox = vi.fn()
        renderWithQueryClient(
            <ValidationView
                schemas={[]}
                selectedDocument={baseDoc}
                selectedDocumentId={docId}
                onValidated={onValidated}
                onBackToInbox={onBackToInbox}
            />,
        )
        await screen.findByDisplayValue('100')

        await user.click(screen.getByRole('button', { name: /Aprovar/i }))
        await waitFor(() => expect(onBackToInbox).toHaveBeenCalled())
        expect(onValidated).toHaveBeenCalled()
    })

    it('rejeitar abre um popup exigindo o motivo', async () => {
        const user = userEvent.setup()
        const onBackToInbox = vi.fn()
        renderWithQueryClient(
            <ValidationView
                schemas={[]}
                selectedDocument={baseDoc}
                selectedDocumentId={docId}
                onValidated={vi.fn()}
                onBackToInbox={onBackToInbox}
            />,
        )
        await screen.findByDisplayValue('100')

        await user.click(screen.getByRole('button', { name: /^Rejeitar$/i }))
        expect(await screen.findByRole('dialog', { name: 'Rejeitar documento' })).toBeInTheDocument()
        // Sem motivo, a confirmação fica desabilitada — não dá pra rejeitar em branco.
        expect(screen.getByRole('button', { name: 'Confirmar rejeição' })).toBeDisabled()
        expect(onBackToInbox).not.toHaveBeenCalled()
    })

    it('rejeita com motivo informado no popup', async () => {
        const user = userEvent.setup()
        const onBackToInbox = vi.fn()
        renderWithQueryClient(
            <ValidationView
                schemas={[]}
                selectedDocument={baseDoc}
                selectedDocumentId={docId}
                onValidated={vi.fn()}
                onBackToInbox={onBackToInbox}
            />,
        )
        await screen.findByDisplayValue('100')

        await user.click(screen.getByRole('button', { name: /^Rejeitar$/i }))
        await user.type(screen.getByPlaceholderText('Motivo da rejeição'), 'Valor divergente')
        await user.click(screen.getByRole('button', { name: 'Confirmar rejeição' }))
        await waitFor(() => expect(onBackToInbox).toHaveBeenCalled())
    })

    it('permite adicionar e remover um campo extraído', async () => {
        const user = userEvent.setup()
        renderWithQueryClient(
            <ValidationView
                schemas={[]}
                selectedDocument={baseDoc}
                selectedDocumentId={docId}
                onValidated={vi.fn()}
                onBackToInbox={vi.fn()}
            />,
        )
        await screen.findByDisplayValue('100')

        await user.click(screen.getByRole('button', { name: 'Adicionar campo' }))
        await user.type(screen.getByPlaceholderText('Nome do campo'), 'numero_pedido')
        await user.type(screen.getByPlaceholderText('Valor'), '42')
        await user.click(screen.getByRole('button', { name: /^Adicionar$/ }))

        // Chave técnica vira rótulo legível ("numero_pedido" -> "Numero Pedido"),
        // não um input de nome cru.
        expect(await screen.findByDisplayValue('42')).toBeInTheDocument()
        expect(screen.getByLabelText('Numero Pedido')).toHaveValue('42')

        await user.click(screen.getByRole('button', { name: 'Remover campo Numero Pedido' }))
        expect(screen.queryByDisplayValue('42')).not.toBeInTheDocument()
    })

    it('abre o histórico de versões (somente leitura)', async () => {
        server.use(
            http.get(`/api/ocr/documents/${docId}/field-versions`, () =>
                HttpResponse.json({
                    results: [
                        {
                            version_number: 1,
                            source_type: 'INITIAL_EXTRACTION',
                            is_active: true,
                            previous_version_number: null,
                            created_at: '2026-06-22T10:00:00Z',
                            created_by: null,
                            fields: { valor: { value: '100', confidence: 0.8 } },
                        },
                    ],
                    count: 1,
                    active_version_number: 1,
                }),
            ),
        )
        const user = userEvent.setup()
        renderValidation()
        await user.type(await screen.findByDisplayValue('100'), '5')

        await user.click(screen.getByRole('button', { name: /Visualizar Histórico/i }))
        expect(await screen.findByText(/Histórico de versões/i)).toBeInTheDocument()
        expect(screen.getByText(/Versão 1/i)).toBeInTheDocument()
    })
})
