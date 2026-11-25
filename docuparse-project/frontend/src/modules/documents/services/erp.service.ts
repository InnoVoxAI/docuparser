import { api } from '../../../shared/lib/http'
import { erpDetailSchema, type ErpDetail } from '../schemas/erp'

/** Estado do lançamento da despesa no ERP e o resumo do que será enviado. */
export async function fetchErpDetail(documentId: string): Promise<ErpDetail> {
    const response = await api.get<unknown>(`/documents/${documentId}/erp`)
    return erpDetailSchema.parse(response.data)
}

/** O analista confirma o envio. O backend registra quem confirmou e quando. */
export async function confirmErpSend(documentId: string): Promise<ErpDetail> {
    const response = await api.post<unknown>(`/documents/${documentId}/erp/confirm`)
    return erpDetailSchema.parse(response.data)
}

/** Reenvio de uma falha retentável (respeita a espera entre tentativas). */
export async function retryErpSend(documentId: string): Promise<ErpDetail> {
    const response = await api.post<unknown>(`/documents/${documentId}/erp/retry`)
    return erpDetailSchema.parse(response.data)
}
