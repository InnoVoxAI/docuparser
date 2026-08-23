import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { RetryStepResult, StepKey } from '../types'
import { processKeys } from './queryKeys'

interface RetryStepInput {
    documentId: string
    step: StepKey
}

async function retryStep({ documentId, step }: RetryStepInput): Promise<RetryStepResult> {
    const response = await api.post<RetryStepResult>(`/documents/${documentId}/retry/${step}`)
    return response.data
}

/** Dispara o retry manual de um step; invalida toda query de `processes`
 * (pipeline do documento + lista da sidebar, cujo `has_error` pode mudar). */
export function useRetryStepMutation() {
    const queryClient = useQueryClient()
    const mutation = useMutation({
        mutationFn: retryStep,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: processKeys.all })
        },
    })
    return { retryStep: mutation.mutateAsync, retrying: mutation.isPending }
}
