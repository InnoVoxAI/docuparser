import { z } from 'zod'

// Formato das listas que o backend serve para montar a revisão da classificação
// (`GET /condominiums` e `GET /condominiums/:id/ledger-accounts`). Campos extras
// são descartados na borda.
export const condominiumOptionSchema = z.object({
    id: z.string(),
    name: z.string(),
    is_active: z.boolean(),
})

export const ledgerAccountSchema = z.object({
    id: z.string(),
    parent_id: z.string().nullable(),
    code: z.string(),
    name: z.string(),
    is_active: z.boolean(),
})

// `GET /documents/:id/account-suggestions`: contas que o fornecedor do documento já usou.
export const accountSuggestionSchema = z.object({
    ledger_account: z.object({ id: z.string(), code: z.string(), name: z.string() }),
    count: z.number(),
    total: z.number(),
    origin: z.string(),
    confident: z.boolean(),
})
export const accountSuggestionsSchema = z.object({
    supplier_known: z.boolean(),
    items: z.array(accountSuggestionSchema),
})

export const condominiumOptionsSchema = z.array(condominiumOptionSchema)
export const ledgerAccountsSchema = z.array(ledgerAccountSchema)

export type CondominiumOption = z.infer<typeof condominiumOptionSchema>
export type LedgerAccount = z.infer<typeof ledgerAccountSchema>
export type AccountSuggestion = z.infer<typeof accountSuggestionSchema>
export type AccountSuggestions = z.infer<typeof accountSuggestionsSchema>
