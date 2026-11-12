import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import {
    createManualProcess,
    decidePaymentProcess,
    fetchCandidates,
    fetchPaymentProcesses,
    undoManualProcess,
} from '../services/payments.service'
import { describeCoverage, describeOrigin, formatCnpj, formatMoney, selectionWarnings } from '../utils'
import type { PaymentDocument } from '../schemas/payments'
import { boletoDoc, invoiceDoc, process } from './fixtures'

const OCR = '/api/ocr'

describe('payments.service', () => {
    it('pede uma página de processos de um status e valida o formato', async () => {
        let query = ''
        server.use(
            http.get(`${OCR}/payment-processes`, ({ request }) => {
                query = new URL(request.url).search
                return HttpResponse.json({
                    results: [{ ...process(), campo_extra: 1 }],
                    count: 1,
                    page: 2,
                    page_size: 10,
                    total_pages: 3,
                })
            }),
        )

        const page = await fetchPaymentProcesses('PENDING', 2)

        expect(query).toContain('status=PENDING')
        expect(query).toContain('page=2')
        expect(page.count).toBe(1)
        expect(page.results[0]).not.toHaveProperty('campo_extra')
    })

    it('recusa um formato inesperado', async () => {
        server.use(
            http.get(`${OCR}/payment-processes`, () =>
                HttpResponse.json({ results: [{ id: 'x', status: 'OUTRO' }], count: 1 }),
            ),
        )

        await expect(fetchPaymentProcesses('PENDING', 1)).rejects.toThrow()
    })

    it.each(['confirm', 'reject'] as const)('envia a decisão %s para o processo', async (decision) => {
        let url = ''
        server.use(
            http.post(`${OCR}/payment-processes/:id/:decision`, ({ request }) => {
                url = new URL(request.url).pathname
                return HttpResponse.json(process({ status: decision === 'confirm' ? 'CONFIRMED' : 'REJECTED' }))
            }),
        )

        const result = await decidePaymentProcess('p1', decision)

        expect(url).toBe(`${OCR}/payment-processes/p1/${decision}`)
        expect(result.status).toBe(decision === 'confirm' ? 'CONFIRMED' : 'REJECTED')
    })
})

describe('utils de pagamentos', () => {
    it('formata CNPJ e valor, e avisa quando a leitura falhou', () => {
        expect(formatCnpj('09769035000164')).toBe('09.769.035/0001-64')
        expect(formatCnpj(null)).toBe('CNPJ não lido')
        expect(formatMoney('1280.00').replace(/\s/g, ' ')).toBe('R$ 1.280,00')
        expect(formatMoney(null)).toBe('valor não lido')
    })

    it('mostra a origem pelo canal', () => {
        const doc = (overrides: Partial<PaymentDocument>) => ({ ...process().invoice, ...overrides })
        expect(describeOrigin(doc({ source_thread_id: 'whatsapp:+5511999999999' }))).toBe('WhatsApp +5511999999999')
        expect(describeOrigin(doc({ source_thread_id: 'email:<a@b>' }))).toBe('E-mail')
        expect(describeOrigin(doc({ source_thread_id: '', channel: 'manual' }))).toBe('Envio manual')
    })

    it('diz quanto da nota os boletos cobrem', () => {
        expect(describeCoverage('900.00', '900.00')).toMatch(/cobrem a nota inteira/)
        expect(describeCoverage('900.00', '600.00')).toMatch(/Faltam/)
        expect(describeCoverage('900.00', '1000.00')).toMatch(/passam da nota/)
        expect(describeCoverage(null, '1.00')).toBe('')
    })
})

describe('pareamento manual', () => {
    it('busca os documentos sem match de um tipo, com a busca e a página', async () => {
        let query = ''
        server.use(
            http.get(`${OCR}/payment-candidates`, ({ request }) => {
                query = new URL(request.url).search
                return HttpResponse.json({
                    results: [invoiceDoc()],
                    count: 1,
                    page: 1,
                    page_size: 10,
                    total_pages: 1,
                })
            }),
        )

        const page = await fetchCandidates('invoice', 'avulsa', 1)

        expect(query).toContain('kind=invoice')
        expect(query).toContain('search=avulsa')
        expect(page.results[0].id).toBe('nf1')
    })

    it('envia a nota e os boletos escolhidos e desfaz a seleção', async () => {
        let body: unknown = null
        let undone = ''
        server.use(
            http.post(`${OCR}/payment-processes/manual`, async ({ request }) => {
                body = await request.json()
                return HttpResponse.json(process({ origin: 'MANUAL' }), { status: 201 })
            }),
            http.post(`${OCR}/payment-processes/:id/undo`, ({ params }) => {
                undone = String(params.id)
                return new HttpResponse(null, { status: 204 })
            }),
        )

        const created = await createManualProcess('nf1', ['bol1', 'bol2'])
        await undoManualProcess('p1')

        expect(body).toEqual({ invoice_id: 'nf1', boleto_ids: ['bol1', 'bol2'] })
        expect(created.origin).toBe('MANUAL')
        expect(undone).toBe('p1')
    })

    it('avisa o que conferir antes de montar o par', () => {
        const invoice = invoiceDoc({ amount: '900.00' })

        expect(selectionWarnings(null, [boletoDoc()])).toEqual([])
        expect(selectionWarnings(invoice, [boletoDoc()])).toEqual([])
        expect(selectionWarnings(invoice, [boletoDoc({ tax_id: '11222333000181' })])[0]).toMatch(/CNPJ.*diferente/)
        expect(selectionWarnings(invoice, [boletoDoc({ tax_id: null })])[0]).toMatch(/CNPJ não foi lido/)
        expect(selectionWarnings(invoice, [boletoDoc({ amount: '1000.00' })])[0]).toMatch(/valor maior/)
        expect(
            selectionWarnings(invoice, [boletoDoc({ amount: '500.00' }), boletoDoc({ id: 'b2', amount: '500.00' })])[0],
        ).toMatch(/somam mais/)
        expect(selectionWarnings(invoice, [boletoDoc({ amount: null })])[0]).toMatch(/valor não foi lido/)
    })
})
