import { z } from 'zod'

// Formato servido por `/charts-of-accounts/:id/supplier-rules`. Campos extras são descartados.
export const ruleSchema = z.object({
    id: z.string(),
    supplier_tax_id: z.string(),
    keyword: z.string(),
    ledger_account_id: z.string(),
    ledger_account: z.object({ id: z.string(), code: z.string(), name: z.string() }),
    is_active: z.boolean(),
    prefills: z.boolean(),
    origin: z.string(),
    evidence_count: z.number(),
    evidence_total: z.number(),
})

export const rulesPageSchema = z.object({ count: z.number(), results: z.array(ruleSchema) })

export type Rule = z.infer<typeof ruleSchema>
export type RulesPage = z.infer<typeof rulesPageSchema>

export interface RuleFilters {
    search: string
    origin: '' | 'history' | 'learned' | 'manual'
    prefills: '' | 'true' | 'false'
    offset: number
}

export const RULES_PAGE_SIZE = 50

/** Regra por CNPJ/CPF ou por nome do fornecedor no documento (sem CNPJ/CPF). */
export interface NewRuleInput {
    supplier_tax_id: string
    keyword: string
    ledger_account_id: string
}

export interface RulePatch {
    ledger_account_id?: string
    is_active?: boolean
}
