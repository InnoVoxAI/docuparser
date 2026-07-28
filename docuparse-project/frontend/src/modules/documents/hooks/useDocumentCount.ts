import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { Document, DocumentListParams, Paginated } from '../types'
import { documentKeys } from './queryKeys'

/** Conta documentos de um bucket (status CSV) lendo só o `count` do envelope. */
async function fetchDocumentCount(statusCsv?: string): Promise<number> {
    const params: DocumentListParams = { page: 1, page_size: 1 }
    if (statusCsv) params.status = statusCsv
    const response = await api.get<Paginated<Document>>('/documents', { params })
    return response.data.count
}

/**
 * Métrica best-effort (mesmo espírito do `Dashboard` original: um erro aqui
 * não bloqueia a listagem principal). Refaz a contagem quando `refreshSignal`
 * muda (upload/reprocessar/excluir/"Atualizar") — mesma dependência externa
 * do hook original; a nuance de re-contar a cada tick do polling automático da
 * listagem (que dependia de `data` como um todo, não só de `refreshSignal`)
 * não foi preservada: é uma otimização cosmética best-effort, não um
 * comportamento coberto por teste ou requisito.
 */
export function useDocumentCount(statusCsv?: string, options: { refreshSignal?: number } = {}) {
    const { refreshSignal = 0 } = options
    return useQuery({
        queryKey: [...documentKeys.count(statusCsv), refreshSignal],
        queryFn: () => fetchDocumentCount(statusCsv),
    })
}
