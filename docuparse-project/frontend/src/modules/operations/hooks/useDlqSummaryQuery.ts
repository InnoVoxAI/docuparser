import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { DlqSummary } from '../types'
import { operationsKeys } from './queryKeys'

const EMPTY_SUMMARY: DlqSummary = { total: 0, streams: [] }

async function fetchDlqSummary(): Promise<DlqSummary> {
    const response = await api.get<DlqSummary>('/operations/dlq/summary')
    return response.data ?? EMPTY_SUMMARY
}

export function useDlqSummaryQuery() {
    const query = useQuery({
        queryKey: operationsKeys.summary(),
        queryFn: fetchDlqSummary,
    })
    return { ...query, data: query.data ?? EMPTY_SUMMARY }
}
