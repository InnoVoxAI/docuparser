import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { settingsKeys } from './queryKeys'

export interface CreateLayoutInput {
    layout: string
    document_type: string
    schema_config_id: string
    confidence_threshold: number
}

/**
 * `createLayout` (POST `/layout-configs`) — ver comentário em `useSchemaMutations`.
 * Catálogo global (spec 018): sem `tenant_slug` no payload.
 */
export function useLayoutMutations() {
    const queryClient = useQueryClient()
    const createMutation = useMutation({
        mutationFn: (payload: CreateLayoutInput) => api.post('/layout-configs', payload),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: settingsKeys.all }),
    })
    return { createLayout: createMutation.mutateAsync }
}
