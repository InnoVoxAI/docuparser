import { beforeEach, describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { renderApp } from '../../../__tests__/utils'
import { process } from './fixtures'

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
