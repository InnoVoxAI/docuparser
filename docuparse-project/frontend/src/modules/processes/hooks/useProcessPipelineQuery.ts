import { useQuery } from '@tanstack/react-query'
import type { Query } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type { ProcessPipeline } from '../types'
import { processKeys } from './queryKeys'

async function fetchPipeline(documentId: string): Promise<ProcessPipeline> {
    const response = await api.get<ProcessPipeline>(`/documents/${documentId}/pipeline`)
    return response.data
}

/**
 * Detalhe do diagrama pro documento selecionado. Poll curto enquanto algum
 * step ainda estiver PENDING — limitação honesta: como uma TaskExecution só
 * é gravada ao FINAL da tentativa, não existe hoje um estado "rodando agora"
 * distinguível de "ainda não começou"; ambos aparecem como PENDING até a
 * task terminar (ou até o usuário disparar um retry manual).
 */
export function useProcessPipelineQuery(documentId: string | null) {
    const query = useQuery({
        queryKey: processKeys.pipeline(documentId ?? ''),
        queryFn: () => fetchPipeline(documentId as string),
        enabled: Boolean(documentId),
        refetchInterval: (currentQuery: Query<ProcessPipeline>) => {
            const currentData = currentQuery.state.data
            if (!currentData) return false
            // Só re-busca enquanto a *ingestão* (ocr/extração) ainda está em
            // andamento. "Validação" e "Classificação" ficam PENDING esperando
            // ação humana / etapa externa — não vale ficar batendo no servidor.
            const ingesting = currentData.steps.some(
                (step) => (step.key === 'ocr' || step.key === 'extraction') && step.status === 'PENDING',
            )
            return ingesting ? 3000 : false
        },
    })

    return {
        data: query.data,
        loading: query.isLoading,
        error: query.error ? readError(query.error, 'Nao foi possivel carregar o processo.') : '',
        refresh: async () => {
            await query.refetch()
        },
    }
}
