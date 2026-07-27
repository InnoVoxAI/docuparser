import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { DlqEvent } from '../types'
import { operationsKeys } from './queryKeys'

const EMPTY_EVENTS: DlqEvent[] = []

async function fetchDlqEvents(stream: string): Promise<DlqEvent[]> {
    const response = await api.get<{ entries?: DlqEvent[] }>('/operations/dlq/events', {
        params: { stream, limit: 50 },
    })
    return response.data?.entries ?? EMPTY_EVENTS
}

export function useDlqEventsQuery(stream: string) {
    const query = useQuery({
        queryKey: operationsKeys.events(stream),
        queryFn: () => fetchDlqEvents(stream),
    })
    return { ...query, data: query.data ?? EMPTY_EVENTS }
}
