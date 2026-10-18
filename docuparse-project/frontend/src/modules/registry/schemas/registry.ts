import { z } from 'zod'

// Formatos servidos por `/condominiums`, `/charts-of-accounts` e `/import/*`.
// Campos extras são descartados na borda.

export const condominiumSchema = z.object({
    id: z.string(),
    name: z.string(),
    cnpj: z.string(),
    external_source: z.string(),
    external_id: z.string(),
    chart_of_accounts_id: z.string().nullable(),
    is_active: z.boolean(),
})

export const chartSchema = z.object({
    id: z.string(),
    name: z.string(),
    external_source: z.string(),
    external_id: z.string(),
    is_active: z.boolean(),
})

export const accountSchema = z.object({
    id: z.string(),
    parent_id: z.string().nullable(),
    code: z.string(),
    name: z.string(),
    is_active: z.boolean(),
})

export const batchSchema = z.object({
    id: z.string(),
    source: z.string(),
    status: z.enum(['running', 'ready', 'error']),
    error_message: z.string(),
    started_by: z.string().nullable(),
    created_at: z.string(),
    finished_at: z.string().nullable(),
})

export const ENTITY_TYPES = ['condominium', 'chart', 'account'] as const
export const ACTIONS = ['conflict', 'new', 'update', 'deactivate'] as const

export const overviewSchema = z.object({
    credentials_configured: z.boolean(),
    latest_batch: batchSchema.nullable(),
    pending_by_action: z.record(z.string(), z.number()),
    pending_by_entity: z.record(z.string(), z.number()),
})

export const proposalSchema = z.object({
    id: z.string(),
    batch_id: z.string(),
    entity_type: z.enum(ENTITY_TYPES),
    external_id: z.string(),
    action: z.enum(ACTIONS),
    data: z.record(z.string(), z.unknown()),
    diff: z.record(z.string(), z.object({ from: z.unknown(), to: z.unknown() })),
    warnings: z.array(z.string()),
    status: z.string(),
    resolution: z.record(z.string(), z.unknown()),
    decided_by: z.string().nullable(),
    decided_at: z.string().nullable(),
    created_at: z.string(),
})

export const proposalsPageSchema = z.object({
    count: z.number(),
    results: z.array(proposalSchema),
})

export const bulkResultSchema = z.object({
    done: z.array(proposalSchema),
    failed: z.array(z.object({ id: z.string(), detail: z.string() })),
})

export const condominiumsSchema = z.array(condominiumSchema)
export const chartsSchema = z.array(chartSchema)
export const accountsSchema = z.array(accountSchema)
export const proposalListSchema = z.array(proposalSchema)

export type Condominium = z.infer<typeof condominiumSchema>
export type Chart = z.infer<typeof chartSchema>
export type Account = z.infer<typeof accountSchema>
export type ImportBatch = z.infer<typeof batchSchema>
export type ImportOverview = z.infer<typeof overviewSchema>
export type Proposal = z.infer<typeof proposalSchema>
export type ProposalsPage = z.infer<typeof proposalsPageSchema>
export type BulkResult = z.infer<typeof bulkResultSchema>
export type EntityType = (typeof ENTITY_TYPES)[number]
export type ProposalAction = (typeof ACTIONS)[number]

export interface ProposalFilters {
    entityType: EntityType
    offset: number
}

export interface NewCondominiumInput {
    name: string
    cnpj: string
    chart_of_accounts_id: string | null
}
