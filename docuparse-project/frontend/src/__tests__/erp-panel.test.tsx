import { describe, it, expect } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { ErpSendPanel } from '../modules/documents'
import { renderWithQueryClient } from './utils'

// Lançamento da despesa no ERP: o analista vê o resumo, confirma e repete falhas passageiras.
const OCR = '/api/ocr'
const docId = 'doc-erp'
const URL = `${OCR}/documents/${docId}/erp`

const summary = {
    condominium: 'Edifício Exemplo',
    supplier: 'Fornecedor Exemplo LTDA',
    supplier_tax_id: '12345678000195',
    account: '2.1.02 Manutenção',
    amount: '1000.00',
    installments: [{ due_date: '2026-07-20', amount: '1000.00' }],
}

function erp(overrides: Record<string, unknown> = {}) {
    return {
        state: 'awaiting_confirmation',
        mode: 'sandbox',
        dry_run: false,
        confirmation_required: true,
        summary,
        errors: [],
        reason: '',
        code: '',
        attempts: 0,
        max_attempts: 5,
        retryable: false,
        exhausted: false,
        can_retry: false,
        next_retry_at: null,
        external_id: '',
        can_confirm: true,
        can_send: true,
        ...overrides,
    }
}

function serve(body: Record<string, unknown>) {
    server.use(http.get(URL, () => HttpResponse.json(body)))
}

function renderPanel() {
    return renderWithQueryClient(<ErpSendPanel documentId={docId} />)
}

describe('Painel do lançamento no ERP', () => {
    it('não aparece quando o documento não tem nada a lançar', async () => {
        serve(erp({ state: 'none', summary: null, can_confirm: false }))
        renderPanel()
        await waitFor(() => expect(screen.queryByLabelText('Lançamento no ERP')).not.toBeInTheDocument())
    })

    it('mostra o resumo do que será lançado antes de confirmar', async () => {
        serve(erp())
        renderPanel()
        const panel = await screen.findByLabelText('Lançamento no ERP')
        expect(within(panel).getByText('Aguardando confirmação')).toBeInTheDocument()
        expect(within(panel).getByText('Edifício Exemplo')).toBeInTheDocument()
        expect(within(panel).getByText('Fornecedor Exemplo LTDA')).toBeInTheDocument()
        expect(within(panel).getByText('2.1.02 Manutenção')).toBeInTheDocument()
        // O valor aparece na linha "Valor" e na parcela do vencimento.
        expect(within(panel).getAllByText(/R\$\s?1\.000,00/)).toHaveLength(2)
        expect(within(panel).getByText(/20\/07\/2026/)).toBeInTheDocument()
    })

    it('só envia depois que o analista confirma no diálogo', async () => {
        let posts = 0
        let sent = false
        server.use(
            http.get(URL, () =>
                HttpResponse.json(sent ? erp({ state: 'sent', can_confirm: false, external_id: '9001' }) : erp()),
            ),
            http.post(`${URL}/confirm`, () => {
                posts += 1
                sent = true
                return HttpResponse.json(erp({ state: 'sent', can_confirm: false, external_id: '9001' }), {
                    status: 202,
                })
            }),
        )
        renderPanel()

        await userEvent.click(await screen.findByRole('button', { name: 'Enviar ao ERP' }))
        const dialog = await screen.findByRole('dialog', { name: 'Enviar esta despesa ao ERP?' })
        expect(within(dialog).getByText(/não pode ser desfeita/)).toBeInTheDocument()
        expect(posts).toBe(0) // abrir o diálogo não envia nada

        await userEvent.click(within(dialog).getByRole('button', { name: 'Enviar ao ERP' }))
        expect(await screen.findByText(/Despesa lançada no ERP \(id 9001\)/)).toBeInTheDocument()
        expect(posts).toBe(1)
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('cancelar o diálogo não envia nada', async () => {
        let posts = 0
        server.use(
            http.get(URL, () => HttpResponse.json(erp())),
            http.post(`${URL}/confirm`, () => {
                posts += 1
                return HttpResponse.json(erp(), { status: 202 })
            }),
        )
        renderPanel()
        await userEvent.click(await screen.findByRole('button', { name: 'Enviar ao ERP' }))
        await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancelar' }))
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
        expect(posts).toBe(0)
    })

    it('quem não tem a permissão vê o resumo, mas não os botões', async () => {
        serve(erp({ can_send: false }))
        renderPanel()
        await screen.findByText('Edifício Exemplo')
        expect(screen.queryByRole('button', { name: 'Enviar ao ERP' })).not.toBeInTheDocument()
    })

    it('lista as pendências que impedem o envio e esconde o botão', async () => {
        serve(
            erp({
                state: 'blocked',
                summary: null,
                can_confirm: false,
                errors: [
                    { code: 'condominium_missing', message: 'O condomínio do documento não foi identificado.' },
                    { code: 'account_missing', message: 'O documento ainda não tem conta classificada.' },
                ],
            }),
        )
        renderPanel()
        expect(await screen.findByText('Corrija antes de enviar:')).toBeInTheDocument()
        expect(screen.getByText('O condomínio do documento não foi identificado.')).toBeInTheDocument()
        expect(screen.getByText('O documento ainda não tem conta classificada.')).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: 'Enviar ao ERP' })).not.toBeInTheDocument()
    })

    it('mostra o motivo da falha e libera "Tentar de novo" quando a espera passou', async () => {
        let retries = 0
        server.use(
            http.get(URL, () =>
                HttpResponse.json(
                    erp({
                        state: 'failed',
                        reason: 'Não foi possível falar com o Superlógica. O pedido pode ou não ter sido aceito.',
                        code: 'network_error',
                        retryable: true,
                        attempts: 1,
                        can_retry: true,
                        can_confirm: false,
                    }),
                ),
            ),
            http.post(`${URL}/retry`, () => {
                retries += 1
                return HttpResponse.json(erp({ state: 'sending', can_confirm: false }), { status: 202 })
            }),
        )
        renderPanel()
        expect(await screen.findByText(/Não foi possível falar com o Superlógica/)).toBeInTheDocument()
        expect(screen.getByText(/Tentativa 1 de 5/)).toBeInTheDocument()
        await userEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
        await waitFor(() => expect(retries).toBe(1))
    })

    it('durante a espera, o reenvio fica desabilitado e diz quando volta', async () => {
        serve(
            erp({
                state: 'failed',
                reason: 'O Superlógica não conseguiu processar agora (HTTP 503).',
                retryable: true,
                attempts: 2,
                can_retry: false,
                next_retry_at: '2026-11-22T15:30:00-03:00',
                can_confirm: false,
            }),
        )
        renderPanel()
        expect(await screen.findByRole('button', { name: 'Tentar de novo' })).toBeDisabled()
        expect(screen.getByText(/Tentativa 2 de 5/)).toBeInTheDocument()
        expect(screen.getByText(/Disponível de novo às/)).toBeInTheDocument()
    })

    it('com as tentativas esgotadas, orienta procurar o suporte', async () => {
        serve(
            erp({
                state: 'failed',
                reason: 'Falha de rede.',
                retryable: true,
                attempts: 5,
                exhausted: true,
                can_retry: false,
                can_confirm: false,
            }),
        )
        renderPanel()
        expect(await screen.findByText(/As tentativas se esgotaram/)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeDisabled()
    })

    it('falha definitiva pede para corrigir o documento e permite enviar de novo', async () => {
        serve(
            erp({
                state: 'failed',
                reason: 'O fornecedor não está cadastrado no Superlógica. Cadastre o fornecedor no ERP e envie de novo.',
                code: 'supplier_not_found',
                retryable: false,
                can_confirm: true,
            }),
        )
        renderPanel()
        expect(await screen.findByText(/Cadastre o fornecedor no ERP/)).toBeInTheDocument()
        expect(screen.getByText('Corrija o documento e envie de novo.')).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: 'Tentar de novo' })).not.toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Enviar ao ERP' })).toBeInTheDocument()
    })

    it('em dry-run o texto deixa claro que nada será enviado', async () => {
        serve(erp({ dry_run: true }))
        renderPanel()
        await userEvent.click(await screen.findByRole('button', { name: 'Simular envio' }))
        const dialog = await screen.findByRole('dialog', { name: 'Simular o envio ao ERP?' })
        expect(within(dialog).getByText(/Nada será enviado/)).toBeInTheDocument()
    })

    it('mostra o erro devolvido pela API dentro do diálogo e mantém o diálogo aberto', async () => {
        server.use(
            http.get(URL, () => HttpResponse.json(erp())),
            http.post(`${URL}/confirm`, () =>
                HttpResponse.json(
                    { detail: 'O documento ainda tem pendências para lançar no ERP.', code: 'invalid' },
                    { status: 422 },
                ),
            ),
        )
        renderPanel()
        await userEvent.click(await screen.findByRole('button', { name: 'Enviar ao ERP' }))
        const dialog = await screen.findByRole('dialog')
        await userEvent.click(within(dialog).getByRole('button', { name: 'Enviar ao ERP' }))
        expect(await within(dialog).findByText(/ainda tem pendências/)).toBeInTheDocument()
    })

    it('consulta de novo enquanto o envio está em andamento e mostra o resultado quando termina', async () => {
        let calls = 0
        server.use(
            http.get(URL, () => {
                calls += 1
                return HttpResponse.json(
                    calls === 1
                        ? erp({ state: 'sending', can_confirm: false })
                        : erp({ state: 'sent', can_confirm: false, external_id: '9001' }),
                )
            }),
        )
        renderPanel()
        expect(await screen.findByText('Enviando ao ERP...')).toBeInTheDocument()
        // O painel repete a consulta sozinho (a cada 3 s) até o estado deixar de ser "enviando".
        expect(await screen.findByText(/Despesa lançada no ERP \(id 9001\)/, {}, { timeout: 6000 })).toBeInTheDocument()
        expect(calls).toBeGreaterThanOrEqual(2)
    }, 10_000)

    it('enquanto o envio está em andamento, avisa e não oferece enviar', async () => {
        serve(erp({ state: 'sending', can_confirm: false }))
        renderPanel()
        expect(await screen.findByText('Enviando ao ERP...')).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: 'Enviar ao ERP' })).not.toBeInTheDocument()
    })
})
