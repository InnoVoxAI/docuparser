import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { LayoutConfig } from '../../../types'
import { settingsKeys } from './queryKeys'

async function fetchLayouts(): Promise<LayoutConfig[]> {
    const response = await api.get<LayoutConfig[]>('/layout-configs')
    return response.data ?? []
}

/** Mesma origem/motivação de `useSchemasQuery` (ver comentário lá). */
export function useLayoutsQuery() {
    const query = useQuery({ queryKey: settingsKeys.layouts(), queryFn: fetchLayouts })
    return { ...query, data: query.data ?? [] }
}
