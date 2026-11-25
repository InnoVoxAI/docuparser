import { describe, expect, it } from 'vitest'
import { buildChecks, type Check } from '../compareChecks'
import type { PaymentDocumentDetail } from '../schemas/payments'
import { boletoDoc, invoiceDoc } from './fixtures'

function detail(fields: Record<string, unknown>, extra: Partial<PaymentDocumentDetail> = {}): PaymentDocumentDetail {
    return {
        id: 'x',
        original_filename: '',
        content_type: 'application/pdf',
        status: '',
        channel: '',
        received_at: '',
        source_thread_id: '',
        extraction_result: { fields },
        condominium: null,
        classification: null,
        metadata: null,
        ...extra,
    }
}

const find = (checks: Check[], id: string) => checks.find((c) => c.id === id)

describe('buildChecks', () => {
    const invoice = invoiceDoc({ amount: '600.00' })
    const boletos = [boletoDoc({ id: 'b1', amount: '300.00' }), boletoDoc({ id: 'b2', amount: '300.00' })]

    it('não compara nada sem a nota ou sem boletos', () => {
        expect(buildChecks(null, boletos, {})).toEqual([])
        expect(buildChecks(invoice, [], {})).toEqual([])
    })

    it('CNPJ igual e valor coberto ficam "ok"', () => {
        const checks = buildChecks(invoice, boletos, {})
        expect(find(checks, 'cnpj')?.tone).toBe('ok')
        expect(find(checks, 'value')?.tone).toBe('ok')
    })

    it('CNPJ diferente ou não lido avisa', () => {
        const other = [boletoDoc({ id: 'b1', tax_id: '98765432000198' })]
        expect(find(buildChecks(invoice, other, {}), 'cnpj')?.tone).toBe('warn')
        const unread = [boletoDoc({ id: 'b1', tax_id: null })]
        expect(find(buildChecks(invoice, unread, {}), 'cnpj')?.text).toMatch(/não foi lido/)
    })

    it('valor faltando é informativo e valor passando da nota avisa', () => {
        const missing = [boletoDoc({ id: 'b1', amount: '300.00' })]
        expect(find(buildChecks(invoice, missing, {}), 'value')).toMatchObject({ tone: 'info' })
        const over = [boletoDoc({ id: 'b1', amount: '700.00' })]
        expect(find(buildChecks(invoice, over, {}), 'value')).toMatchObject({ tone: 'warn' })
    })

    it('valor não lido avisa', () => {
        expect(find(buildChecks(invoiceDoc({ amount: null }), boletos, {}), 'value')?.tone).toBe('warn')
    })

    it('compara o pagador dos boletos com o tomador da nota só depois de carregar os dados', () => {
        expect(find(buildChecks(invoice, boletos, {}), 'payer')).toBeUndefined()
        const details = {
            [invoice.id]: detail({ cnpj_tomador: '11.222.333/0001-81' }),
            b1: detail({ cnpj_cpf_pagador: '11222333000181' }),
            b2: detail({ cnpj_cpf_pagador: '11222333000181' }),
        }
        expect(find(buildChecks(invoice, boletos, details), 'payer')?.tone).toBe('ok')
    })

    it('pagador diferente do tomador alerta que pode ser de outro condomínio', () => {
        const details = {
            [invoice.id]: detail({ cnpj_tomador: '11222333000181' }),
            b1: detail({ cnpj_cpf_pagador: '11222333000181' }),
            b2: detail({ cnpj_cpf_pagador: '44555666000100' }),
        }
        const check = find(buildChecks(invoice, boletos, details), 'payer')
        expect(check?.tone).toBe('warn')
        expect(check?.text).toMatch(/outro condomínio/)
    })

    it('lista os vencimentos em ordem e avisa quando falta algum', () => {
        const details = {
            [invoice.id]: detail({}),
            b1: detail({ data_vencimento: '2026-08-20' }),
            b2: detail({ data_vencimento: '10/07/2026' }),
        }
        expect(find(buildChecks(invoice, boletos, details), 'due')?.text).toBe('10/07/2026 · 20/08/2026')
        const missing = { ...details, b2: detail({}) }
        expect(find(buildChecks(invoice, boletos, missing), 'due')?.tone).toBe('warn')
    })

    it('diz se os documentos chegaram juntos', () => {
        expect(find(buildChecks(invoice, boletos, {}), 'origin')?.tone).toBe('ok')
        const apart = [boletoDoc({ id: 'b1', source_thread_id: 'email:<outro@x>' })]
        expect(find(buildChecks(invoice, apart, {}), 'origin')?.tone).toBe('info')
    })

    it('mostra o condomínio e a conta da nota, ou avisa que não foi identificado', () => {
        const withCondo = detail(
            {},
            {
                condominium: { id: 'c1', name: 'Edifício Exemplo' },
                classification: { ledger_account: { code: '2.1.02', name: 'Manutenção' } },
            },
        )
        const ok = find(buildChecks(invoice, boletos, { [invoice.id]: withCondo }), 'condominium')
        expect(ok?.text).toBe('Edifício Exemplo · Conta 2.1.02 Manutenção')
        const none = find(buildChecks(invoice, boletos, { [invoice.id]: detail({}) }), 'condominium')
        expect(none?.tone).toBe('warn')
    })
})
