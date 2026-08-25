import type { ProcessListParams } from '../types'

export const processKeys = {
    all: ['processes'] as const,
    list: (params: ProcessListParams) => [...processKeys.all, 'list', params] as const,
    pipeline: (documentId: string) => [...processKeys.all, 'pipeline', documentId] as const,
}
