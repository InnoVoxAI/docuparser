import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { ValidationView } from '../modules/documents'
import type { Document } from '../types'
import { renderWithQueryClient } from './utils'

// Revisão/override da conta classificada pelo operador, na tela de validação.
const OCR = '/api/ocr'
const docId = 'doc-1'

const accounts = [
    { id: 'root', parent_id: null, code: '2', name: 'Despesas', is_active: true },
    { id: 'water', parent_id: 'root', code: '2.1.01', name: 'Água', is_active: true },
    { id: 'maint', parent_id: 'root', code: '2.3.01', name: 'Manutenções', is_active: true },
    { id: 'old', parent_id: 'root', code: '2.9.99', name: 'Conta antiga', is_active: false },
]

const suggested = {
    ledger_account: { id: 'water', code: '2.1.01', name: 'Água' },
    origin: 'automatic' as const,
    rule_id: 'supplier',
    reason: 'fornecedor 09769035000164',
    classified_by: null,
    updated_at: '2026-10-14T10:00:00Z',
}

function buildDoc(overrides: Partial<Document> = {}): Document {
    return {
        id: docId,
        status: 'VALIDATION_PENDING',
        channel: 'manual',
        original_filename: 'fatura.pdf',
        content_type: 'application/pdf',
        active_field_version_number: 1,
        extraction_result: {
            schema_id: 's',
            schema_version: 'v1',
            fields: { valor: { value: '100', confidence: 0.8 } },
            confidence: 0.8,
            requires_human_validation: true,
        },
        condominium: { id: 'c1', name: 'Edifício Exemplo' },
        classification: suggested,
        ...overrides,
    }
}

function useAccounts() {
    server.use(http.get(`${OCR}/condominiums/c1/ledger-accounts`, () => HttpResponse.json(accounts)))
}

/** O seletor fica desabilitado ("Carregando...") até a lista de contas chegar. */
async function accountSelect() {
    const select = await screen.findByLabelText('Conta do plano de contas')
    await waitFor(() => expect(select).toBeEnabled())
    return select
}

function renderReview(doc: Document, onValidated = vi.fn()) {
    renderWithQueryClient(
        <ValidationView
            schemas={[]}
            selectedDocument={doc}
            selectedDocumentId={docId}
            onValidated={onValidated}
            onBackToInbox={vi.fn()}
        />,
    )
    return onValidated
}

describe('Revisão da classificação', () => {
    it('mostra a conta sugerida, o condomínio e o motivo', async () => {
        useAccounts()
        renderReview(buildDoc())

        expect(await screen.findByText('2.1.01 · Água')).toBeInTheDocument()
        expect(screen.getByText('Edifício Exemplo')).toBeInTheDocument()
        expect(screen.getByText(/Sugerida automaticamente \(fornecedor 09769035000164\)/)).toBeInTheDocument()
    })

    it('lista só contas ativas e sem filhas, na ordem do código', async () => {
        useAccounts()
        renderReview(buildDoc())

        const select = await accountSelect()
        const labels = Array.from(select.querySelectorAll('option')).map((option) => option.textContent)
        expect(labels).toEqual(['Selecione...', '2.1.01 · Água', '2.3.01 · Manutenções'])
    })

    it('só habilita Alterar conta quando outra conta é escolhida', async () => {
        useAccounts()
        renderReview(buildDoc())

        const button = await screen.findByRole('button', { name: 'Alterar conta' })
        expect(button).toBeDisabled()
        await userEvent.selectOptions(await accountSelect(), 'maint')
        expect(button).toBeEnabled()
    })

    it('envia o override ao backend e recarrega o documento', async () => {
        useAccounts()
        let sent: unknown = null
        server.use(
            http.put(`${OCR}/documents/${docId}/ledger-account`, async ({ request }) => {
                sent = await request.json()
                return HttpResponse.json({ origin: 'manual' })
            }),
        )
        const onValidated = renderReview(buildDoc())

        await userEvent.selectOptions(await accountSelect(), 'maint')
        await userEvent.click(screen.getByRole('button', { name: 'Alterar conta' }))

        await waitFor(() => expect(onValidated).toHaveBeenCalled())
        expect(sent).toEqual({ ledger_account_id: 'maint' })
    })

    it('mostra quem definiu a conta quando foi o operador', async () => {
        useAccounts()
        renderReview(
            buildDoc({
                classification: {
                    ...suggested,
                    ledger_account: { id: 'maint', code: '2.3.01', name: 'Manutenções' },
                    origin: 'manual',
                    classified_by: 'ana@condo.test',
                },
            }),
        )
        expect(await screen.findByText('Definida por ana@condo.test')).toBeInTheDocument()
    })

    it('mostra o motivo devolvido pelo backend quando o override é recusado', async () => {
        useAccounts()
        server.use(
            http.put(`${OCR}/documents/${docId}/ledger-account`, () =>
                HttpResponse.json(
                    { ledger_account_id: ['A conta precisa ser do condomínio do documento.'] },
                    { status: 400 },
                ),
            ),
        )
        const onValidated = renderReview(buildDoc())

        await userEvent.selectOptions(await accountSelect(), 'maint')
        await userEvent.click(screen.getByRole('button', { name: 'Alterar conta' }))

        expect(await screen.findByText('A conta precisa ser do condomínio do documento.')).toBeInTheDocument()
        expect(onValidated).not.toHaveBeenCalled()
    })

    it('sem sugestão, convida o operador a escolher uma conta', async () => {
        useAccounts()
        renderReview(buildDoc({ classification: null }))
        expect(await screen.findByText('Nenhuma conta foi sugerida. Escolha uma abaixo.')).toBeInTheDocument()
    })

    it('sem condomínio, pede para definir o condomínio e envia a escolha', async () => {
        server.use(
            http.get(`${OCR}/condominiums`, () =>
                HttpResponse.json([
                    { id: 'c1', name: 'Edifício Exemplo', is_active: true },
                    { id: 'c2', name: 'Edifício Inativo', is_active: false },
                ]),
            ),
        )
        let sent: unknown = null
        server.use(
            http.put(`${OCR}/documents/${docId}/condominium`, async ({ request }) => {
                sent = await request.json()
                return HttpResponse.json({ condominium_id: 'c1' })
            }),
        )
        const onValidated = renderReview(buildDoc({ condominium: null, classification: null }))

        const select = await screen.findByLabelText('Condomínio do documento')
        await waitFor(() => expect(select).toBeEnabled())
        await userEvent.selectOptions(select, 'c1')
        await userEvent.click(screen.getByRole('button', { name: 'Definir condomínio' }))

        await waitFor(() => expect(onValidated).toHaveBeenCalled())
        expect(sent).toEqual({ condominium_id: 'c1' })
    })

    it('permite corrigir um condomínio identificado errado', async () => {
        useAccounts()
        server.use(
            http.get(`${OCR}/condominiums`, () =>
                HttpResponse.json([
                    { id: 'c1', name: 'Edifício Exemplo', is_active: true },
                    { id: 'c2', name: 'Edifício Outro', is_active: true },
                ]),
            ),
        )
        renderReview(buildDoc())

        await userEvent.click(await screen.findByRole('button', { name: 'Alterar condomínio' }))
        expect(await screen.findByLabelText('Condomínio do documento')).toBeInTheDocument()
        await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
        expect(screen.queryByLabelText('Condomínio do documento')).not.toBeInTheDocument()
    })

    it('some para quem não usa o plano de contas', async () => {
        renderReview(buildDoc({ condominium: null, classification: null }))

        await screen.findByDisplayValue('100')
        await waitFor(() => expect(screen.queryByText('Classificação contábil')).not.toBeInTheDocument())
    })

    it('depois da decisão, mostra a conta mas não deixa alterar', async () => {
        useAccounts()
        renderReview(buildDoc({ status: 'APPROVED' }))

        expect(await screen.findByText('2.1.01 · Água')).toBeInTheDocument()
        expect(screen.getByText(/não pode mais ser alterada/)).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: 'Alterar conta' })).not.toBeInTheDocument()
        expect(screen.queryByRole('button', { name: 'Alterar condomínio' })).not.toBeInTheDocument()
    })
})
