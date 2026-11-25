import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { readError } from '../../../shared/utils'
import { confirmErpSend, fetchErpDetail, retryErpSend } from '../services/erp.service'
import { erpKeys } from './queryKeys'

const POLL_WHILE_SENDING_MS = 3_000

/** Estado do lançamento no ERP; consulta de novo enquanto o envio está em andamento. */
export function useErpDetail(documentId: string, options: { enabled?: boolean } = {}) {
    return useQuery({
        queryKey: erpKeys.detail(documentId),
        queryFn: () => fetchErpDetail(documentId),
        enabled: (options.enabled ?? true) && Boolean(documentId),
        refetchInterval: (query) => (query.state.data?.state === 'sending' ? POLL_WHILE_SENDING_MS : false),
    })
}

/** Confirmar o envio e repetir uma falha retentável. */
export function useErpActions(documentId: string, onChanged?: () => void | Promise<unknown>) {
    const queryClient = useQueryClient()
    const refresh = async () => {
        await queryClient.invalidateQueries({ queryKey: erpKeys.detail(documentId) })
        await onChanged?.()
    }
    const confirm = useMutation({ mutationFn: () => confirmErpSend(documentId), onSuccess: refresh })
    const retry = useMutation({ mutationFn: () => retryErpSend(documentId), onSuccess: refresh })
    const failure = confirm.error ?? retry.error
    return {
        // O erro fica em `error`; as ações nunca rejeitam, para não escapar do clique.
        confirm: async (): Promise<boolean> => {
            try {
                await confirm.mutateAsync()
                return true
            } catch {
                return false
            }
        },
        retry: () => retry.mutate(),
        busy: confirm.isPending || retry.isPending,
        error: failure ? readError(failure, 'Não foi possível enviar ao ERP.') : '',
        reset: () => {
            confirm.reset()
            retry.reset()
        },
    }
}
