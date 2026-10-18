import { api } from '../../../shared/lib/http'
import {
    accountsSchema,
    batchSchema,
    bulkResultSchema,
    chartsSchema,
    condominiumSchema,
    condominiumsSchema,
    overviewSchema,
    proposalListSchema,
    proposalSchema,
    proposalsPageSchema,
    type Account,
    type BulkResult,
    type Chart,
    type Condominium,
    type ImportBatch,
    type ImportOverview,
    type NewCondominiumInput,
    type Proposal,
    type ProposalFilters,
    type ProposalsPage,
} from '../schemas/registry'

export const PROPOSALS_PAGE_SIZE = 100

export async function fetchCondominiums(): Promise<Condominium[]> {
    const response = await api.get<unknown>('/condominiums')
    return condominiumsSchema.parse(response.data)
}

export async function fetchCharts(): Promise<Chart[]> {
    const response = await api.get<unknown>('/charts-of-accounts')
    return chartsSchema.parse(response.data)
}

export async function fetchChartAccounts(chartId: string): Promise<Account[]> {
    const response = await api.get<unknown>(`/charts-of-accounts/${chartId}/ledger-accounts`)
    return accountsSchema.parse(response.data)
}

export async function createCondominium(input: NewCondominiumInput): Promise<Condominium> {
    const response = await api.post<unknown>('/condominiums', input)
    return condominiumSchema.parse(response.data)
}

export async function fetchOverview(): Promise<ImportOverview> {
    const response = await api.get<unknown>('/import/overview')
    return overviewSchema.parse(response.data)
}

/** Inicia a leitura do Superlógica em segundo plano; o andamento vem do overview. */
export async function startSync(): Promise<ImportBatch> {
    const response = await api.post<unknown>('/import/sync')
    return batchSchema.parse(response.data)
}

export async function fetchProposals({ entityType, offset }: ProposalFilters): Promise<ProposalsPage> {
    const response = await api.get<unknown>('/import/proposals', {
        params: { entity_type: entityType, limit: PROPOSALS_PAGE_SIZE, offset },
    })
    return proposalsPageSchema.parse(response.data)
}

export async function approveProposal(id: string): Promise<Proposal> {
    const response = await api.post<unknown>(`/import/proposals/${id}/approve`)
    return proposalSchema.parse(response.data)
}

export async function rejectProposal(id: string): Promise<Proposal> {
    const response = await api.post<unknown>(`/import/proposals/${id}/reject`)
    return proposalSchema.parse(response.data)
}

/** A escolha vale para todos os registros do mesmo conflito, que voltam resolvidos. */
export async function resolveProposal(id: string, resolution: Record<string, unknown>): Promise<Proposal[]> {
    const response = await api.post<unknown>(`/import/proposals/${id}/resolve`, { resolution })
    return proposalListSchema.parse(response.data)
}

export async function approveProposals(ids: string[]): Promise<BulkResult> {
    const response = await api.post<unknown>('/import/proposals/approve', { ids })
    return bulkResultSchema.parse(response.data)
}

export async function rejectProposals(ids: string[]): Promise<BulkResult> {
    const response = await api.post<unknown>('/import/proposals/reject', { ids })
    return bulkResultSchema.parse(response.data)
}
