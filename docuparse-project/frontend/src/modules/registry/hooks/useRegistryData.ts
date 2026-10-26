import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { NewCondominiumInput } from '../schemas/registry'
import {
    createCondominium,
    fetchChartAccounts,
    fetchCharts,
    fetchCondominiums,
    fetchOverview,
    startSync,
} from '../services/registry.service'
import { registryKeys } from './queryKeys'

const STALE_MS = 30_000
const SYNC_POLL_MS = 2_000

export function useCondominiums() {
    return useQuery({ queryKey: registryKeys.condominiums(), queryFn: fetchCondominiums, staleTime: STALE_MS })
}

export function useCharts() {
    return useQuery({ queryKey: registryKeys.charts(), queryFn: fetchCharts, staleTime: STALE_MS })
}

export function useChartAccounts(chartId: string | null) {
    return useQuery({
        queryKey: registryKeys.accounts(chartId ?? ''),
        queryFn: () => fetchChartAccounts(chartId ?? ''),
        enabled: Boolean(chartId),
        staleTime: STALE_MS,
    })
}

/** Estado da importação; consulta de 2 em 2 s enquanto uma sincronização está em andamento. */
export function useImportOverview({ enabled = true }: { enabled?: boolean } = {}) {
    return useQuery({
        queryKey: registryKeys.overview(),
        queryFn: fetchOverview,
        enabled,
        staleTime: 5_000,
        // Telas que abrem logo depois de salvar as credenciais não podem confiar no cache anterior.
        refetchOnMount: 'always',
        refetchInterval: (query) => (query.state.data?.latest_batch?.status === 'running' ? SYNC_POLL_MS : false),
    })
}

export function useCreateCondominium() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: (input: NewCondominiumInput) => createCondominium(input),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: registryKeys.condominiums() }),
    })
}

export function useStartSync() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: startSync,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: registryKeys.overview() }),
    })
}
