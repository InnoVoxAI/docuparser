import type { DocumentListParams } from '../types'

export const documentKeys = {
    all: ['documents'] as const,
    list: (params: DocumentListParams) => [...documentKeys.all, 'list', params] as const,
    count: (statusCsv?: string) => [...documentKeys.all, 'count', statusCsv] as const,
    detail: (id: string) => [...documentKeys.all, 'detail', id] as const,
    fieldVersions: (id: string) => [...documentKeys.detail(id), 'field-versions'] as const,
}
