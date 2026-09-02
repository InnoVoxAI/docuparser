import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Query } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type { Paginated, ProcessListParams, ProcessStatusGroup, ProcessSummary } from '../types'
import { processKeys } from './queryKeys'

const PAGE_SIZE = 25

// Enquanto algum processo da página estiver num destes status, a lista ainda
// está "se movendo" — vale re-buscar de tempos em tempos pra refletir o avanço
// do pipeline sem o usuário precisar recarregar.
const NON_TERMINAL_STATUSES = new Set(['RECEIVED', 'OCR_COMPLETED', 'EXTRACTION_COMPLETED', 'VALIDATION_PENDING'])

const EMPTY_PAGE: Paginated<ProcessSummary> = {
    results: [],
    count: 0,
    page: 1,
    page_size: PAGE_SIZE,
    total_pages: 0,
}

async function fetchProcessPage(params: ProcessListParams): Promise<Paginated<ProcessSummary>> {
    const response = await api.get<Paginated<ProcessSummary>>('/processes', { params })
    return response.data
}

/** Lista paginada de processos pra tabela da Visão Geral, filtrável pelos
 * chips de status "de negócio" (multi-seleção). */
export function useProcessesQuery() {
    const [page, setPage] = useState(1)
    const [statusGroups, setStatusGroups] = useState<ProcessStatusGroup[]>([])

    const params: ProcessListParams = { page, page_size: PAGE_SIZE }
    if (statusGroups.length) params.status_group = statusGroups.join(',')

    const query = useQuery({
        queryKey: processKeys.list(params),
        queryFn: () => fetchProcessPage(params),
        placeholderData: keepPreviousData,
        staleTime: 2000,
        refetchInterval: (currentQuery: Query<Paginated<ProcessSummary>>) => {
            const currentData = currentQuery.state.data
            if (!currentData) return false
            const stillMoving = currentData.results.some((process) => NON_TERMINAL_STATUSES.has(process.status))
            return stillMoving ? 4000 : false
        },
    })

    const goToPage = (next: number) => setPage(Math.max(next, 1))

    const toggleStatusGroup = (group: ProcessStatusGroup) => {
        setPage(1)
        setStatusGroups((prev) => (prev.includes(group) ? prev.filter((item) => item !== group) : [...prev, group]))
    }

    const clearStatusGroups = () => {
        setPage(1)
        setStatusGroups([])
    }

    return {
        page,
        goToPage,
        statusGroups,
        toggleStatusGroup,
        clearStatusGroups,
        data: query.data ?? EMPTY_PAGE,
        loading: query.isLoading,
        fetching: query.isFetching,
        error: query.error ? readError(query.error, 'Nao foi possivel carregar os processos.') : '',
        refresh: async () => {
            await query.refetch()
        },
    }
}
