import { useQueries } from '@tanstack/react-query'
import type { PaymentDocumentDetail } from '../schemas/payments'
import { fetchPaymentDocument } from '../services/payments.service'
import { paymentKeys } from './queryKeys'

export interface DocumentDetailState {
    detail: PaymentDocumentDetail | undefined
    loading: boolean
    error: boolean
}

/** Dados completos dos documentos do popup, indexados por id (uma consulta por documento). */
export function usePaymentDocuments(ids: string[]): Record<string, DocumentDetailState> {
    const queries = useQueries({
        queries: ids.map((id) => ({
            queryKey: paymentKeys.document(id),
            queryFn: () => fetchPaymentDocument(id),
            staleTime: 60_000,
        })),
    })
    return Object.fromEntries(
        ids.map((id, index) => [
            id,
            {
                detail: queries[index]?.data,
                loading: Boolean(queries[index]?.isLoading),
                error: Boolean(queries[index]?.isError),
            },
        ]),
    )
}
