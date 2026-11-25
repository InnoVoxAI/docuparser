import { api } from '../../../shared/lib/http'
import {
    candidatePageSchema,
    paymentDocumentDetailSchema,
    paymentProcessPageSchema,
    paymentProcessSchema,
    type CandidateKind,
    type CandidatePage,
    type Decision,
    type PaymentDocumentDetail,
    type PaymentProcess,
    type PaymentProcessPage,
    type ProcessStatus,
} from '../schemas/payments'

export const PAGE_SIZE = 10

export async function fetchPaymentProcesses(status: ProcessStatus, page: number): Promise<PaymentProcessPage> {
    const response = await api.get<unknown>('/payment-processes', {
        params: { status, page, page_size: PAGE_SIZE },
    })
    return paymentProcessPageSchema.parse(response.data)
}

/** Confirmar ou rejeitar o agrupamento. O backend registra quem decidiu e quando. */
export async function decidePaymentProcess(processId: string, decision: Decision): Promise<PaymentProcess> {
    const response = await api.post<unknown>(`/payment-processes/${processId}/${decision}`)
    return paymentProcessSchema.parse(response.data)
}

/** Notas fiscais ou boletos fora de qualquer agrupamento pendente ou confirmado. */
export async function fetchCandidates(kind: CandidateKind, search: string, page: number): Promise<CandidatePage> {
    const response = await api.get<unknown>('/payment-candidates', {
        params: { kind, search: search || undefined, page, page_size: PAGE_SIZE },
    })
    return candidatePageSchema.parse(response.data)
}

/** Monta o par à mão. O agrupamento nasce pendente e segue o mesmo fluxo de confirmação. */
export async function createManualProcess(invoiceId: string, boletoIds: string[]): Promise<PaymentProcess> {
    const response = await api.post<unknown>('/payment-processes/manual', {
        invoice_id: invoiceId,
        boleto_ids: boletoIds,
    })
    return paymentProcessSchema.parse(response.data)
}

/** Desfaz a seleção manual ainda pendente: os documentos voltam à lista de sem match. */
export async function undoManualProcess(processId: string): Promise<void> {
    await api.post(`/payment-processes/${processId}/undo`)
}

/** Dados completos de um documento do agrupamento, para o popup de comparação. */
export async function fetchPaymentDocument(documentId: string): Promise<PaymentDocumentDetail> {
    const response = await api.get<unknown>(`/documents/${documentId}`)
    return paymentDocumentDetailSchema.parse(response.data)
}
