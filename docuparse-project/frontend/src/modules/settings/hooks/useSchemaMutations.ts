import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { SchemaConfig } from '../../../types'
import { settingsKeys } from './queryKeys'

export interface SaveSchemaInput {
    id?: string
    schema_id: string
    version: string
    definition: Record<string, unknown>
    is_active: boolean
}

/**
 * `createSchema`/`saveDraft` (POST/PATCH `/schema-configs`) e a exclusão de
 * `DeleteSchemaModal` (DELETE `/schema-configs/:id`), antes chamadas axios
 * soltas seguidas de `onChanged()`/`refreshData()` manual, convertidas para
 * `useMutation` invalidando `settingsKeys.all` em `onSuccess` — consequência
 * necessária de remover `schemas`/`layouts` de `AppOutletContext` (decisão
 * #7 do handoff de T036-T040), mesmo padrão de `useDocumentMutations`.
 *
 * O catálogo de schemas/layouts é global (spec 018): não há mais `tenant_slug`
 * no payload — o backend serve o mesmo catálogo para todos os tenants e a
 * escrita exige a permissão de plataforma `tenants.manage`.
 */
export function useSchemaMutations() {
    const queryClient = useQueryClient()
    const invalidate = () => queryClient.invalidateQueries({ queryKey: settingsKeys.all })

    const saveMutation = useMutation({
        mutationFn: ({ id, ...payload }: SaveSchemaInput) =>
            id
                ? api.patch<SchemaConfig>(`/schema-configs/${id}`, payload)
                : api.post<SchemaConfig>('/schema-configs', payload),
        onSuccess: invalidate,
    })

    const deleteMutation = useMutation({
        mutationFn: (id: string) => api.delete(`/schema-configs/${id}`),
        onSuccess: invalidate,
    })

    return {
        saveSchema: saveMutation.mutateAsync,
        deleteSchema: deleteMutation.mutateAsync,
        deleting: deleteMutation.isPending,
    }
}
