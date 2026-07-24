import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { operationsKeys } from './queryKeys'

export interface RequeueEventInput {
    stream: string
    id?: string
    execute: boolean
}

interface RequeueEventResult {
    target_stream?: string
}

async function requeueEvent(input: RequeueEventInput): Promise<RequeueEventResult> {
    const response = await api.post<RequeueEventResult>('/operations/dlq/requeue', {
        stream: input.stream,
        id: input.id,
        execute: input.execute,
        requested_by: 'frontend-admin',
    })
    return response.data ?? {}
}

/**
 * `execute: false` é apenas simulação (não altera a DLQ, não invalida cache).
 * `execute: true` reenfileira de fato — invalida `operationsKeys.all` (cobre
 * summary + eventos de qualquer stream, por prefixo de chave), mesmo efeito
 * do `loadOperations(selectedStream)` completo do código original.
 */
export function useRequeueMutation() {
    const queryClient = useQueryClient()
    const mutation = useMutation({
        mutationFn: requeueEvent,
        onSuccess: (_result, variables) => {
            if (variables.execute) {
                queryClient.invalidateQueries({ queryKey: operationsKeys.all })
            }
        },
    })
    return { requeueEvent: mutation.mutateAsync, requeueing: mutation.isPending }
}
