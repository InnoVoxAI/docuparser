import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { BulkResult, EntityType } from '../schemas/registry'
import {
    approveProposal,
    approveProposals,
    fetchProposals,
    rejectProposal,
    rejectProposals,
    resolveProposal,
} from '../services/registry.service'
import { readFieldError } from '../utils'
import { registryKeys } from './queryKeys'

/**
 * Propostas pendentes de um tipo de entidade, com paginação e as decisões do
 * analista. Decidir pode mudar o cadastro (condomínios, planos, contas), então
 * invalida tudo do módulo.
 */
export function useProposalReview(entityType: EntityType, batchKey: string, enabled = true) {
    const queryClient = useQueryClient()
    const [offset, setOffset] = useState(0)
    const [bulkResult, setBulkResult] = useState<BulkResult | null>(null)
    const filters = { entityType, offset }

    const query = useQuery({
        queryKey: registryKeys.proposals(filters, batchKey),
        queryFn: () => fetchProposals(filters),
        enabled,
        placeholderData: keepPreviousData,
        staleTime: 5_000,
    })

    const refresh = () => queryClient.invalidateQueries({ queryKey: registryKeys.all })

    const approve = useMutation({ mutationFn: approveProposal, onSettled: refresh })
    const reject = useMutation({ mutationFn: rejectProposal, onSettled: refresh })
    const resolve = useMutation({
        mutationFn: (input: { id: string; resolution: Record<string, unknown> }) =>
            resolveProposal(input.id, input.resolution),
        onSettled: refresh,
    })
    const bulk = useMutation({
        mutationFn: (input: { ids: string[]; decision: 'approve' | 'reject' }) =>
            input.decision === 'approve' ? approveProposals(input.ids) : rejectProposals(input.ids),
        onSuccess: (result) => setBulkResult(result),
        onSettled: refresh,
    })

    const actionError = approve.error ?? reject.error ?? resolve.error ?? bulk.error

    return {
        page: query.data,
        loading: query.isLoading,
        loadError: query.error ? readFieldError(query.error, 'Nao foi possivel carregar as propostas.') : '',
        offset,
        setOffset,
        // `mutate` e não `mutateAsync`: a recusa da API aparece em `actionError`, sem rejeição solta.
        approve: approve.mutate,
        reject: reject.mutate,
        resolve: resolve.mutate,
        decideMany: bulk.mutate,
        busy: approve.isPending || reject.isPending || resolve.isPending || bulk.isPending,
        actionError: actionError ? readFieldError(actionError, 'Nao foi possivel concluir a decisao.') : '',
        bulkResult,
        clearBulkResult: () => setBulkResult(null),
        resetErrors: () => {
            approve.reset()
            reject.reset()
            resolve.reset()
            bulk.reset()
        },
    }
}
