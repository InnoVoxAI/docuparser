import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Query } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type {
    Paginated,
    ProcessListParams,
    ProcessOrderingField,
    ProcessStatusGroup,
    ProcessSummary,
    SortDirection,
} from '../types'
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

/** Lista paginada de processos pra tabela da Visão Geral, filtrável por busca
 * (nome do arquivo) e pelo status "de negócio" (dropdown — um status por vez,
 * ou "Todos"). */
export function useProcessesQuery() {
    const [page, setPage] = useState(1)
    const [statusGroup, setStatusGroupState] = useState<ProcessStatusGroup | ''>('')
    const [search, setSearchState] = useState('')
    // `null` = sem ordenação explícita (default do backend: mais recente primeiro).
    const [sort, setSort] = useState<{ field: ProcessOrderingField; direction: SortDirection } | null>(null)

    const params: ProcessListParams = { page, page_size: PAGE_SIZE }
    if (statusGroup) params.status_group = statusGroup
    const term = search.trim()
    if (term) params.search = term
    if (sort) params.ordering = sort.direction === 'desc' ? `-${sort.field}` : sort.field

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

    const setStatusGroup = (group: ProcessStatusGroup | '') => {
        setPage(1)
        setStatusGroupState(group)
    }

    const setSearch = (value: string) => {
        setPage(1)
        setSearchState(value)
    }

    // Clique num cabeçalho de coluna: não estava ordenando por ela -> ascendente;
    // já estava ascendente -> descendente; já estava descendente -> limpa (volta
    // ao default). Mesmo ciclo de 3 estados usado em tabelas do estilo GitHub/Notion.
    const toggleSort = (field: ProcessOrderingField) => {
        setPage(1)
        setSort((current) => {
            if (!current || current.field !== field) return { field, direction: 'asc' }
            if (current.direction === 'asc') return { field, direction: 'desc' }
            return null
        })
    }

    return {
        page,
        goToPage,
        statusGroup,
        setStatusGroup,
        search,
        setSearch,
        sort,
        toggleSort,
        data: query.data ?? EMPTY_PAGE,
        loading: query.isLoading,
        fetching: query.isFetching,
        error: query.error ? readError(query.error, 'Nao foi possivel carregar os processos.') : '',
        refresh: async () => {
            await query.refetch()
        },
    }
}
