import { useMemo } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { readError } from '../../../shared/utils'
import { readClassificationError, selectableAccounts } from '../classification'
import {
    fetchCondominiums,
    fetchLedgerAccounts,
    setDocumentCondominium,
    setDocumentLedgerAccount,
} from '../services/classification.service'
import type { Document } from '../types'
import { classificationKeys } from './queryKeys'

const STALE_MS = 60_000

/**
 * Dados e ações da revisão da conta classificada (override do operador).
 * As contas só são buscadas quando o documento já tem condomínio; a lista de
 * condomínios, só quando falta definir (ou corrigir) o condomínio.
 */
export function useClassificationReview({
    document,
    editingCondominium,
    onChanged,
}: {
    document: Document
    editingCondominium: boolean
    onChanged: () => void | Promise<unknown>
}) {
    const condominiumId = document.condominium?.id ?? ''

    const accountsQuery = useQuery({
        queryKey: classificationKeys.accounts(condominiumId),
        queryFn: () => fetchLedgerAccounts(condominiumId),
        enabled: Boolean(condominiumId),
        staleTime: STALE_MS,
    })
    const condominiumsQuery = useQuery({
        queryKey: classificationKeys.condominiums(),
        queryFn: fetchCondominiums,
        enabled: !condominiumId || editingCondominium,
        staleTime: STALE_MS,
    })

    const accountMutation = useMutation({
        mutationFn: (ledgerAccountId: string) => setDocumentLedgerAccount(document.id, ledgerAccountId),
        onSuccess: async () => {
            await onChanged()
        },
    })
    const condominiumMutation = useMutation({
        mutationFn: (newCondominiumId: string) => setDocumentCondominium(document.id, newCondominiumId),
        onSuccess: async () => {
            await onChanged()
        },
    })

    const accountOptions = useMemo(() => selectableAccounts(accountsQuery.data ?? []), [accountsQuery.data])
    const condominiumOptions = useMemo(
        () => (condominiumsQuery.data ?? []).filter((condominium) => condominium.is_active),
        [condominiumsQuery.data],
    )

    return {
        accounts: {
            options: accountOptions,
            loading: accountsQuery.isLoading,
            loadError: accountsQuery.error
                ? readError(accountsQuery.error, 'Nao foi possivel carregar o plano de contas.')
                : '',
            save: accountMutation.mutateAsync,
            saving: accountMutation.isPending,
            saveError: accountMutation.error
                ? readClassificationError(accountMutation.error, 'Nao foi possivel alterar a conta.')
                : '',
            saved: accountMutation.isSuccess,
        },
        condominiums: {
            options: condominiumOptions,
            loading: condominiumsQuery.isLoading,
            loadError: condominiumsQuery.error
                ? readError(condominiumsQuery.error, 'Nao foi possivel carregar os condominios.')
                : '',
            save: condominiumMutation.mutateAsync,
            saving: condominiumMutation.isPending,
            saveError: condominiumMutation.error
                ? readClassificationError(condominiumMutation.error, 'Nao foi possivel definir o condominio.')
                : '',
        },
    }
}
