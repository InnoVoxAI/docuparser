import type { DocumentListParams } from '../types'

export const documentKeys = {
    all: ['documents'] as const,
    list: (params: DocumentListParams) => [...documentKeys.all, 'list', params] as const,
    count: (statusCsv?: string) => [...documentKeys.all, 'count', statusCsv] as const,
    detail: (id: string) => [...documentKeys.all, 'detail', id] as const,
    fieldVersions: (id: string) => [...documentKeys.detail(id), 'field-versions'] as const,
}

export const classificationKeys = {
    all: ['classification'] as const,
    condominiums: () => [...classificationKeys.all, 'condominiums'] as const,
    accounts: (condominiumId: string) => [...classificationKeys.all, 'accounts', condominiumId] as const,
}
