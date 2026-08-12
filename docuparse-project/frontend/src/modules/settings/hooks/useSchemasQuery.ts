import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { SchemaConfig } from '../../../types'
import { settingsKeys } from './queryKeys'

async function fetchSchemas(): Promise<SchemaConfig[]> {
    const response = await api.get<SchemaConfig[]>('/schema-configs')
    return response.data ?? []
}

/**
 * Antes um `useState` preenchido pelo `refreshData` de `AppLayout`
 * (`main.tsx`), fatiado para `AppOutletContext.schemas`. Agora um `useQuery`
 * próprio do módulo — schemas/layouts saem de `AppOutletContext` por completo
 * (decisão #5 do handoff de T036-T040); `modules/documents` (Validação)
 * consome via este mesmo hook, importado do barrel de `settings`.
 */
export function useSchemasQuery() {
    const query = useQuery({ queryKey: settingsKeys.schemas(), queryFn: fetchSchemas })
    return { ...query, data: query.data ?? [] }
}
