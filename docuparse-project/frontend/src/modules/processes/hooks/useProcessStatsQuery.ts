import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type { ProcessStats } from '../types'
import { processKeys } from './queryKeys'

async function fetchStats(): Promise<ProcessStats> {
    const response = await api.get<ProcessStats>('/processes/stats')
    return response.data
}

/** Números agregados de todos os processos pra tela de Estatísticas. */
export function useProcessStatsQuery() {
    const query = useQuery({
        queryKey: processKeys.stats(),
        queryFn: fetchStats,
        staleTime: 10_000,
        refetchInterval: 20_000,
    })

    return {
        data: query.data,
        loading: query.isLoading,
        error: query.error ? readError(query.error, 'Nao foi possivel carregar as estatisticas.') : '',
    }
}
