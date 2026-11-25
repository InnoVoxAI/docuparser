import { describe, expect, it } from 'vitest'
import { displayField, digitsOf, isoDate, moneyOf, rawField } from '../documentFields'
import type { PaymentDocumentDetail } from '../schemas/payments'

function detail(fields: Record<string, unknown>): PaymentDocumentDetail {
    return {
        id: 'd1',
        original_filename: 'x.pdf',
        content_type: 'application/pdf',
        status: '',
        channel: '',
        received_at: '',
        source_thread_id: '',
        extraction_result: { fields },
        condominium: null,
        classification: null,
        metadata: null,
    }
}

describe('documentFields', () => {
    it('lê o campo tanto como {value, confidence} quanto como valor simples', () => {
        const d = detail({ a: { value: '10', confidence: 0.9 }, b: 'direto', c: 5 })
        expect(rawField(d, ['a'])).toBe('10')
        expect(rawField(d, ['b'])).toBe('direto')
        expect(rawField(d, ['c'])).toBe('5')
    })

    it('usa o primeiro campo com valor e ignora o texto "Valor não encontrado"', () => {
        const d = detail({ valor_boleto: { value: 'Valor não encontrado' }, valor_documento: { value: '1000,00' } })
        expect(rawField(d, ['valor_boleto', 'valor_documento'])).toBe('1000,00')
        expect(rawField(detail({}), ['x'])).toBe('')
        expect(rawField(undefined, ['x'])).toBe('')
    })

    it('entende valores em formato brasileiro e americano', () => {
        expect(moneyOf('1.000,50')).toBe(1000.5)
        expect(moneyOf('R$ 344,50')).toBe(344.5)
        expect(moneyOf('1000.50')).toBe(1000.5)
        expect(moneyOf('abc')).toBeNull()
        expect(moneyOf('')).toBeNull()
    })

    it('entende datas ISO e brasileiras', () => {
        expect(isoDate('2026-07-20')).toBe('2026-07-20')
        expect(isoDate('20/07/2026')).toBe('2026-07-20')
        expect(isoDate('20/07/2026 10:30:00')).toBe('2026-07-20')
        expect(isoDate('lixo')).toBe('')
    })

    it('formata dinheiro, data, CNPJ e CPF para mostrar', () => {
        const d = detail({ v: '1000.00', dt: '2026-07-20', cnpj: '12345678000195', cpf: '12345678909' })
        expect(displayField(d, { label: 'v', keys: ['v'], format: 'money' })).toMatch(/R\$\s?1\.000,00/)
        expect(displayField(d, { label: 'dt', keys: ['dt'], format: 'date' })).toBe('20/07/2026')
        expect(displayField(d, { label: 'c', keys: ['cnpj'], format: 'tax_id' })).toBe('12.345.678/0001-95')
        expect(displayField(d, { label: 'p', keys: ['cpf'], format: 'tax_id' })).toBe('123.456.789-09')
    })

    it('devolve vazio quando o campo não foi lido, para a tela mostrar "não lido"', () => {
        expect(displayField(detail({}), { label: 'x', keys: ['x'], format: 'money' })).toBe('')
    })

    it('extrai só os dígitos de um CNPJ formatado', () => {
        expect(digitsOf('12.345.678/0001-95')).toBe('12345678000195')
    })
})
