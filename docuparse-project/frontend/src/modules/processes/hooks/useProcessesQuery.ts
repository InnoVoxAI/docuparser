import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Query } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type { Paginated, ProcessFilter, ProcessListParams, ProcessSummary, StepKey } from '../types'
import { processKeys } from './queryKeys'

const PAGE_SIZE = 25

const NON_TERMINAL_STATUSES = new Set([
    'RECEIVED',
    'OCR_COMPLETED',
    'EXTRACTION_COMPLETED',
    'VALIDATION_PENDING',
])

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

/** Lista paginada de processos (documentos enviados) pra sidebar do dashboard. */
export function useProcessesQuery() {
    const [page, setPage] = useState(1)
    const [search, setSearchState] = useState('')
    const [filter, setFilterState] = useState<ProcessFilter | ''>('')
    const [stage, setStageState] = useState<StepKey | ''>('')

    const params: ProcessListParams = { page, page_size: PAGE_SIZE }
    const term = search.trim()
    if (term) params.search = term
    if (filter) params.filter = filter
    if (stage) params.stage = stage

    const query = useQuery({
        queryKey: processKeys.list(params),
        queryFn: () => fetchProcessPage(params),
        placeholderData: keepPreviousData,
        refetchInterval: (currentQuery: Query<Paginated<ProcessSummary>>) => {
            const currentData = currentQuery.state.data
            if (!currentData) return false
            const stillMoving = currentData.results.some((process) => NON_TERMINAL_STATUSES.has(process.status))
            return stillMoving ? 4000 : false
        },
    })

    const setSearch = (value: string) => {
        setSearchState(value)
        setPage(1)
    }

    const setFilter = (value: ProcessFilter | '') => {
        setFilterState(value)
        setPage(1)
    }

    const setStage = (value: StepKey | '') => {
        setStageState(value)
        setPage(1)
    }

    return {
        page,
        setPage,
        search,
        setSearch,
        filter,
        setFilter,
        stage,
        setStage,
        data: query.data ?? EMPTY_PAGE,
        loading: query.isLoading,
        error: query.error ? readError(query.error, 'Nao foi possivel carregar os processos.') : '',
        refresh: async () => {
            await query.refetch()
        },
    }
}
