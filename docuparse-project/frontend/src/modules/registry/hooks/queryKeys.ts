import type { ProposalFilters } from '../schemas/registry'
import type { RuleFilters } from '../schemas/rules'

export const registryKeys = {
    all: ['registry'] as const,
    condominiums: () => [...registryKeys.all, 'condominiums'] as const,
    charts: () => [...registryKeys.all, 'charts'] as const,
    accounts: (chartId: string) => [...registryKeys.all, 'accounts', chartId] as const,
    rules: (chartId: string, filters: RuleFilters) => [...registryKeys.all, 'rules', chartId, filters] as const,
    overview: () => [...registryKeys.all, 'overview'] as const,
    proposals: (filters: ProposalFilters, batchKey: string) =>
        [...registryKeys.all, 'proposals', filters, batchKey] as const,
}
