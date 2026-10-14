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

export const condominiumOptionsSchema = z.array(condominiumOptionSchema)
export const ledgerAccountsSchema = z.array(ledgerAccountSchema)

export type CondominiumOption = z.infer<typeof condominiumOptionSchema>
export type LedgerAccount = z.infer<typeof ledgerAccountSchema>
