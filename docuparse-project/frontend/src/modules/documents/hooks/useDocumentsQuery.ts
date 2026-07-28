import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Query } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type { Document, DocumentListParams, Paginated } from '../types'
import { documentKeys } from './queryKeys'

const PAGE_SIZE = 25

const EMPTY_PAGE: Paginated<Document> = { results: [], count: 0, page: 1, page_size: PAGE_SIZE, total_pages: 0 }

async function fetchDocumentPage(params: DocumentListParams): Promise<Paginated<Document>> {
    const response = await api.get<Paginated<Document>>('/documents', { params })
    return response.data
}

/**
 * Estado de uma listagem paginada server-side de documentos (feature 009),
 * agora sobre TanStack Query — preserva a assinatura de retorno consumida
 * pelas telas (page/setPage/search/setSearch/data/loading/error/refresh).
 * `refresh` continua expondo apenas um `refresh()` sem argumentos: a
 * distinção "silenciosa vs. com loading" do hook original vira, aqui, a
 * diferença entre `isLoading` (primeiro fetch) e `isFetching` em segundo
 * plano (refetch via `refetchInterval`, que não reseta `data`).
 */
export function useDocumentsQuery(statusCsv?: string, options: { autoRefresh?: boolean; refreshSignal?: number } = {}) {
    const { autoRefresh = false, refreshSignal = 0 } = options
    const [page, setPage] = useState(1)
    const [search, setSearchState] = useState('')

    const params: DocumentListParams = { page, page_size: PAGE_SIZE }
    if (statusCsv) params.status = statusCsv
    const term = search.trim()
    if (term) params.search = term

    const query = useQuery({
        queryKey: [...documentKeys.list(params), refreshSignal],
        queryFn: () => fetchDocumentPage(params),
        placeholderData: keepPreviousData,
        refetchInterval: (currentQuery: Query<Paginated<Document>>) => {
            if (!autoRefresh) return false
            const currentData = currentQuery.state.data
            if (!currentData) return false
            const processing = currentData.results.some(
                (document) => document.status === 'RECEIVED' || document.status === 'OCR_COMPLETED',
            )
            return processing ? 4000 : false
        },
    })

    const setSearch = (value: string) => {
        setSearchState(value)
        setPage(1)
    }

    return {
        page,
        setPage,
        search,
        setSearch,
        data: query.data ?? EMPTY_PAGE,
        loading: query.isLoading,
        error: query.error ? readError(query.error, 'Nao foi possivel carregar os documentos.') : '',
        refresh: async () => {
            await query.refetch()
        },
    }
}
