import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { readError } from '../../../shared/utils'
import type { Decision, ProcessStatus } from '../schemas/payments'
import { decidePaymentProcess, fetchPaymentProcesses } from '../services/payments.service'
import { paymentKeys } from './queryKeys'

/** Processos de pagamento de um status, uma página por vez. */
export function usePaymentProcesses(status: ProcessStatus, page: number, options: { enabled?: boolean } = {}) {
    return useQuery({
        queryKey: paymentKeys.processes(status, page),
        queryFn: () => fetchPaymentProcesses(status, page),
        placeholderData: keepPreviousData,
        staleTime: 10_000,
        enabled: options.enabled ?? true,
    })
}

/** Quantos processos esperam o operador (para o selo do menu). */
export function usePendingPaymentCount(options: { enabled?: boolean } = {}) {
    return usePaymentProcesses('PENDING', 1, options).data?.count ?? 0
}

export function usePaymentDecision() {
    const queryClient = useQueryClient()
    const mutation = useMutation({
        mutationFn: (input: { processId: string; decision: Decision }) =>
            decidePaymentProcess(input.processId, input.decision),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: paymentKeys.all }),
    })
    return {
        decide: mutation.mutateAsync,
        busy: mutation.isPending,
        error: mutation.error ? readError(mutation.error, 'Não foi possível registrar a decisão.') : '',
        reset: mutation.reset,
    }
}
