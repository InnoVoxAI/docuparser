import { api } from '../../../shared/lib/http'
import {
    paymentProcessPageSchema,
    paymentProcessSchema,
    type Decision,
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
