import { beforeEach, describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { renderApp } from '../../../__tests__/utils'
import { boletoDoc, invoiceDoc, process } from './fixtures'

const OCR = '/api/ocr'

function mockMe(permissions: string[]) {
    server.use(
        http.get('/api/auth/me', () =>
            HttpResponse.json({ id: 'u1', name: 'User', email: 'u@docuparse.local', permissions }),
        ),
    )
}

const page = (results: ReturnType<typeof process>[]) => ({
    results,
    count: results.length,
    page: 1,
    page_size: 10,
    total_pages: results.length ? 1 : 0,
})

describe('Pagamentos (revisão dos agrupamentos de nota e boletos)', () => {
    beforeEach(() => localStorage.setItem('access_token', 'tok'))

    it('mostra a nota e os boletos do agrupamento pendente com o que falta cobrir', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        server.use(http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process()]))))

        renderApp('/payments')

        const card = await screen.findByRole('article', { name: 'Processo de pagamento' })
        expect(within(card).getByText('nota.pdf')).toBeInTheDocument()
        expect(within(card).getByText('boleto-1.pdf')).toBeInTheDocument()
        expect(within(card).getByText('boleto-2.pdf')).toBeInTheDocument()
        expect(within(card).getByText(/Aguardando confirmação/)).toBeInTheDocument()
        expect(within(card).getByText(/Faltam/)).toBeInTheDocument()
        expect(within(card).getAllByText(/09\.769\.035\/0001-64/).length).toBeGreaterThan(0)
    })

    it('confirma o agrupamento e avisa o operador', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        let confirmed = false
        server.use(
            http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page(confirmed ? [] : [process()]))),
            http.post(`${OCR}/payment-processes/p1/confirm`, () => {
                confirmed = true
                return HttpResponse.json(process({ status: 'CONFIRMED', decided_by: 'op' }))
            }),
        )

        renderApp('/payments')
        await userEvent.click(await screen.findByRole('button', { name: /Confirmar/ }))

        expect(await screen.findByText('Processo de pagamento confirmado.')).toBeInTheDocument()
        await waitFor(() => expect(screen.queryByRole('article')).not.toBeInTheDocument())
    })

    it('pede confirmação antes de rejeitar e só então envia', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        let rejected = 0
        server.use(
            http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process()]))),
            http.post(`${OCR}/payment-processes/p1/reject`, () => {
                rejected += 1
                return HttpResponse.json(process({ status: 'REJECTED' }))
            }),
        )

        renderApp('/payments')
        await userEvent.click(await screen.findByRole('button', { name: /Rejeitar/ }))
        const dialog = await screen.findByRole('dialog')
        expect(rejected).toBe(0)
        await userEvent.click(within(dialog).getByRole('button', { name: 'Rejeitar' }))

        expect(await screen.findByText('Agrupamento rejeitado.')).toBeInTheDocument()
        expect(rejected).toBe(1)
    })

    it('mostra o motivo quando o backend recusa a decisão', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        server.use(
            http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process()]))),
            http.post(`${OCR}/payment-processes/p1/confirm`, () =>
                HttpResponse.json(
                    { detail: 'Algum boleto já foi confirmado em outro processo de pagamento.', code: 'boleto_taken' },
                    { status: 409 },
                ),
            ),
        )

        renderApp('/payments')
        await userEvent.click(await screen.findByRole('button', { name: /Confirmar/ }))

        expect(await screen.findByText(/já foi confirmado em outro processo/)).toBeInTheDocument()
    })

    it('sem a permissão de validar, mostra o agrupamento mas sem os botões de decisão', async () => {
        mockMe(['inbox.view'])
        server.use(http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process()]))))

        renderApp('/payments')

        await screen.findByRole('article', { name: 'Processo de pagamento' })
        expect(screen.queryByRole('button', { name: /Confirmar/ })).not.toBeInTheDocument()
        expect(screen.queryByRole('button', { name: /Rejeitar/ })).not.toBeInTheDocument()
    })

    it('troca de aba para ver os confirmados, com quem decidiu e quando', async () => {
        mockMe(['inbox.view'])
        server.use(
            http.get(`${OCR}/payment-processes`, ({ request }) => {
                const status = new URL(request.url).searchParams.get('status')
                return HttpResponse.json(
                    page(
                        status === 'CONFIRMED'
                            ? [
                                  process({
                                      status: 'CONFIRMED',
                                      decided_by: 'maria',
                                      decided_at: '2026-11-11T09:00:00Z',
                                  }),
                              ]
                            : [],
                    ),
                )
            }),
        )

        renderApp('/payments')
        await screen.findByText(/Nenhum processo de pagamento nesta situação/)
        await userEvent.click(screen.getByRole('tab', { name: 'Confirmados' }))

        expect(await screen.findByText(/Confirmado por maria/)).toBeInTheDocument()
    })

    it('o menu leva à tela e mostra quantos agrupamentos esperam revisão', async () => {
        mockMe(['inbox.view'])
        server.use(
            http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process(), process({ id: 'p2' })]))),
        )

        renderApp('/')
        await userEvent.click(await screen.findByRole('button', { name: 'Abrir menu' }))

        const link = await screen.findByRole('link', { name: /Pagamentos/ })
        expect(within(link).getByText('2')).toBeInTheDocument()
    })
})

describe('Pagamentos (sem match e pareamento manual)', () => {
    beforeEach(() => localStorage.setItem('access_token', 'tok'))

    function mockPool(boletos = [boletoDoc()], invoices = [invoiceDoc()]) {
        server.use(
            http.get(`${OCR}/payment-candidates`, ({ request }) => {
                const results = new URL(request.url).searchParams.get('kind') === 'invoice' ? invoices : boletos
                return HttpResponse.json({ results, count: results.length, page: 1, page_size: 10, total_pages: 1 })
            }),
        )
    }

    async function openUnmatched() {
        renderApp('/payments')
        await userEvent.click(await screen.findByRole('tab', { name: 'Sem match' }))
    }

    it('lista as notas e os boletos sem match, cada um na sua coluna', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        mockPool()

        await openUnmatched()

        const invoices = await screen.findByRole('region', { name: 'Notas fiscais' })
        const boletos = screen.getByRole('region', { name: 'Boletos' })
        expect(within(invoices).getByText('nota-avulsa.pdf')).toBeInTheDocument()
        expect(within(boletos).getByText('boleto-avulso.pdf')).toBeInTheDocument()
    })

    it('filtra a lista pela busca', async () => {
        mockMe(['inbox.view'])
        const searches: string[] = []
        server.use(
            http.get(`${OCR}/payment-candidates`, ({ request }) => {
                searches.push(new URL(request.url).searchParams.get('search') ?? '')
                return HttpResponse.json({ results: [], count: 0, page: 1, page_size: 10, total_pages: 0 })
            }),
        )

        await openUnmatched()
        const invoices = await screen.findByRole('region', { name: 'Notas fiscais' })
        await userEvent.type(within(invoices).getByRole('searchbox'), 'cora')

        await waitFor(() => expect(searches).toContain('cora'))
    })

    it('monta o par escolhido, cria o agrupamento pendente e leva à revisão', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        mockPool()
        let body: unknown = null
        server.use(
            http.post(`${OCR}/payment-processes/manual`, async ({ request }) => {
                body = await request.json()
                return HttpResponse.json(process({ origin: 'MANUAL' }), { status: 201 })
            }),
        )

        await openUnmatched()
        await userEvent.click(await screen.findByLabelText('Selecionar nota-avulsa.pdf'))
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))
        await userEvent.click(screen.getByRole('button', { name: /Montar agrupamento/ }))

        expect(await screen.findByText(/Agrupamento montado/)).toBeInTheDocument()
        expect(body).toEqual({ invoice_id: 'nf1', boleto_ids: ['bol1'] })
        expect(screen.getByRole('tab', { name: 'Para revisar', selected: true })).toBeInTheDocument()
    })

    it('desfaz a seleção antes de montar, sem chamar o backend', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        mockPool()
        let calls = 0
        server.use(
            http.post(`${OCR}/payment-processes/manual`, () => {
                calls += 1
                return HttpResponse.json(process(), { status: 201 })
            }),
        )

        await openUnmatched()
        const invoiceBox = await screen.findByLabelText('Selecionar nota-avulsa.pdf')
        await userEvent.click(invoiceBox)
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))
        expect(invoiceBox).toBeChecked()
        await userEvent.click(screen.getByRole('button', { name: /Desfazer seleção/ }))

        expect(invoiceBox).not.toBeChecked()
        expect(screen.getByLabelText('Selecionar boleto-avulso.pdf')).not.toBeChecked()
        expect(screen.getByRole('button', { name: /Montar agrupamento/ })).toBeDisabled()
        expect(calls).toBe(0)
    })

    it('avisa quando o par escolhido não bate e deixa o operador decidir', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        mockPool([boletoDoc({ tax_id: '11222333000181' })])

        await openUnmatched()
        await userEvent.click(await screen.findByLabelText('Selecionar nota-avulsa.pdf'))
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))

        expect(screen.getByText(/CNPJ de algum boleto é diferente/)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Montar agrupamento/ })).toBeEnabled()
    })

    it('mostra o motivo quando o backend recusa o par', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        mockPool()
        server.use(
            http.post(`${OCR}/payment-processes/manual`, () =>
                HttpResponse.json(
                    {
                        detail: 'A nota já tem um agrupamento aguardando decisão. Decida-o primeiro.',
                        code: 'invoice_busy',
                    },
                    { status: 409 },
                ),
            ),
        )

        await openUnmatched()
        await userEvent.click(await screen.findByLabelText('Selecionar nota-avulsa.pdf'))
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))
        await userEvent.click(screen.getByRole('button', { name: /Montar agrupamento/ }))

        expect(await screen.findByText(/já tem um agrupamento aguardando decisão/)).toBeInTheDocument()
    })

    it('sem a permissão de validar, só consulta: não há barra de seleção', async () => {
        mockMe(['inbox.view'])
        mockPool()

        await openUnmatched()

        await screen.findByText('nota-avulsa.pdf')
        expect(screen.queryByRole('button', { name: /Montar agrupamento/ })).not.toBeInTheDocument()
    })

    it('desfaz um agrupamento manual ainda pendente e devolve os documentos ao pool', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        let undone = 0
        server.use(
            http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process({ origin: 'MANUAL' })]))),
            http.post(`${OCR}/payment-processes/p1/undo`, () => {
                undone += 1
                return new HttpResponse(null, { status: 204 })
            }),
        )

        renderApp('/payments')
        expect(await screen.findByText('Montado à mão', { exact: false })).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: 'Rejeitar' })).not.toBeInTheDocument()
        await userEvent.click(screen.getByRole('button', { name: /Desfazer seleção/ }))

        expect(await screen.findByText(/Seleção desfeita/)).toBeInTheDocument()
        expect(undone).toBe(1)
    })

    it('o agrupamento automático continua com Rejeitar, sem Desfazer', async () => {
        mockMe(['inbox.view', 'documents.validate'])
        server.use(http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process()]))))

        renderApp('/payments')

        expect(await screen.findByRole('button', { name: /Rejeitar/ })).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: /Desfazer seleção/ })).not.toBeInTheDocument()
    })
})
