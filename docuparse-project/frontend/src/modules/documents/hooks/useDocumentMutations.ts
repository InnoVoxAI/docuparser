import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { documentKeys } from './queryKeys'

export interface ValidateDocumentInput {
    id: string
    decision: 'approved' | 'rejected'
    notes: string
    correctedFields: Record<string, string>
}

/**
 * Mutações de documento (reprocessar/excluir/validar-aprovar-rejeitar)
 * convertidas de chamadas axios soltas para `useMutation`, invalidando
 * `documentKeys.all` em `onSuccess` — qualquer `useDocumentsQuery`/
 * `useDocumentCount` ativo refaz a busca automaticamente, substituindo o
 * `refreshSignal` manual para este caso (mantido em paralelo por outros
 * consumidores ainda não migrados, ver `AppLayout`).
 */
export function useDocumentMutations() {
    const queryClient = useQueryClient()
    const invalidateDocuments = () => queryClient.invalidateQueries({ queryKey: documentKeys.all })

    const reprocessMutation = useMutation({
        mutationFn: (id: string) => api.post(`/documents/${id}/reprocess-ocr`),
        onSuccess: invalidateDocuments,
    })

    const deleteMutation = useMutation({
        mutationFn: (id: string) => api.delete(`/documents/${id}/delete`),
        onSuccess: invalidateDocuments,
    })

    const validateMutation = useMutation({
        mutationFn: ({ id, decision, notes, correctedFields }: ValidateDocumentInput) =>
            api.post(`/documents/${id}/validate`, { decision, notes, corrected_fields: correctedFields }),
        onSuccess: invalidateDocuments,
    })

    return {
        reprocessDocument: reprocessMutation.mutateAsync,
        deleteDocument: deleteMutation.mutateAsync,
        validateDocument: validateMutation.mutateAsync,
    }
}
