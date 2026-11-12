import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { readError } from '../../../shared/utils'
import type { CandidateKind } from '../schemas/payments'
import { createManualProcess, fetchCandidates, undoManualProcess } from '../services/payments.service'
import { paymentKeys } from './queryKeys'

/** Notas ou boletos sem match, filtrados por busca, uma página por vez. */
export function useCandidates(kind: CandidateKind, search: string, page: number) {
    return useQuery({
        queryKey: paymentKeys.candidates(kind, search, page),
        queryFn: () => fetchCandidates(kind, search, page),
        placeholderData: keepPreviousData,
        staleTime: 10_000,
    })
}

/** Montar o par à mão e desfazer a seleção pendente. */
export function useManualMatch() {
    const queryClient = useQueryClient()
    const refresh = () => queryClient.invalidateQueries({ queryKey: paymentKeys.all })
    const create = useMutation({
        mutationFn: (input: { invoiceId: string; boletoIds: string[] }) =>
            createManualProcess(input.invoiceId, input.boletoIds),
        onSuccess: refresh,
    })
    const undo = useMutation({ mutationFn: (processId: string) => undoManualProcess(processId), onSuccess: refresh })
    const failure = create.error ?? undo.error
    return {
        create: create.mutateAsync,
        undo: undo.mutateAsync,
        busy: create.isPending || undo.isPending,
        error: failure ? readError(failure, 'Não foi possível salvar a seleção.') : '',
        reset: () => {
            create.reset()
            undo.reset()
        },
    }
}
