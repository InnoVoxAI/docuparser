import type { PaymentDocument, PaymentProcess } from '../schemas/payments'

const doc = (overrides: Partial<PaymentDocument>): PaymentDocument => ({
    id: 'd1',
    original_filename: 'nota.pdf',
    document_type: 'nota_fiscal',
    status: 'VALIDATION_PENDING',
    channel: 'email',
    source_thread_id: 'email:<msg-1@example.test>',
    received_at: '2026-11-10T10:00:00Z',
    tax_id: '09769035000164',
    amount: '900.00',
    ...overrides,
})

export function process(overrides: Partial<PaymentProcess> = {}): PaymentProcess {
    return {
        id: 'p1',
        status: 'PENDING',
        origin: 'AUTOMATIC',
        invoice: doc({}),
        boletos: [
            doc({ id: 'b1', original_filename: 'boleto-1.pdf', document_type: 'boleto', amount: '300.00' }),
            doc({ id: 'b2', original_filename: 'boleto-2.pdf', document_type: 'boleto', amount: '300.00' }),
        ],
        invoice_amount: '900.00',
        boletos_total: '600.00',
        decided_by: null,
        decided_at: null,
        created_at: '2026-11-10T10:05:00Z',
        ...overrides,
    }
}
