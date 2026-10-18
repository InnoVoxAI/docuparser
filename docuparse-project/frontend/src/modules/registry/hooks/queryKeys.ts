import type { ProposalFilters } from '../schemas/registry'

export const registryKeys = {
    all: ['registry'] as const,
    condominiums: () => [...registryKeys.all, 'condominiums'] as const,
    charts: () => [...registryKeys.all, 'charts'] as const,
    accounts: (chartId: string) => [...registryKeys.all, 'accounts', chartId] as const,
    overview: () => [...registryKeys.all, 'overview'] as const,
    proposals: (filters: ProposalFilters, batchKey: string) =>
        [...registryKeys.all, 'proposals', filters, batchKey] as const,
}
