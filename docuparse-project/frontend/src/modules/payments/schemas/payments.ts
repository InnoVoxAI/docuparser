import { z } from 'zod'

export const PROCESS_STATUSES = ['PENDING', 'CONFIRMED', 'REJECTED'] as const
export type ProcessStatus = (typeof PROCESS_STATUSES)[number]

// Formato servido por `/payment-processes`. Campos extras são descartados.
export const paymentDocumentSchema = z.object({
    id: z.string(),
    original_filename: z.string(),
    document_type: z.string(),
    status: z.string(),
    channel: z.string(),
    source_thread_id: z.string(),
    received_at: z.string(),
    tax_id: z.string().nullable(),
    amount: z.string().nullable(),
})

export const paymentProcessSchema = z.object({
    id: z.string(),
    status: z.enum(PROCESS_STATUSES),
    origin: z.enum(['AUTOMATIC', 'MANUAL']),
    invoice: paymentDocumentSchema,
    boletos: z.array(paymentDocumentSchema),
    invoice_amount: z.string().nullable(),
    boletos_total: z.string().nullable(),
    decided_by: z.string().nullable(),
    decided_at: z.string().nullable(),
    created_at: z.string(),
})

export const paymentProcessPageSchema = z.object({
    results: z.array(paymentProcessSchema),
    count: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
})

export const candidatePageSchema = z.object({
    results: z.array(paymentDocumentSchema),
    count: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
})

export type CandidatePage = z.infer<typeof candidatePageSchema>
export type CandidateKind = 'invoice' | 'boleto'
export type PaymentDocument = z.infer<typeof paymentDocumentSchema>
export type PaymentProcess = z.infer<typeof paymentProcessSchema>
export type PaymentProcessPage = z.infer<typeof paymentProcessPageSchema>

export type Decision = 'confirm' | 'reject'
