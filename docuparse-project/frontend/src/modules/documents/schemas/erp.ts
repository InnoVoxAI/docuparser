import { z } from 'zod'
import { ERP_STATES, type ErpState } from '../../../shared/utils'

const installmentSchema = z.object({ due_date: z.string(), amount: z.string() })

/** O que será lançado no ERP, montado pelo backend a partir do documento aprovado. */
export const erpSummarySchema = z.object({
    condominium: z.string(),
    supplier: z.string(),
    supplier_tax_id: z.string(),
    account: z.string(),
    amount: z.string(),
    installments: z.array(installmentSchema),
})

const erpIssueSchema = z.object({ code: z.string(), message: z.string() })

export const erpDetailSchema = z.object({
    state: z.enum(ERP_STATES),
    mode: z.string(),
    dry_run: z.boolean(),
    confirmation_required: z.boolean(),
    summary: erpSummarySchema.nullable(),
    errors: z.array(erpIssueSchema),
    reason: z.string(),
    code: z.string(),
    attempts: z.number(),
    max_attempts: z.number(),
    retryable: z.boolean(),
    exhausted: z.boolean(),
    can_retry: z.boolean(),
    next_retry_at: z.string().nullable(),
    external_id: z.string(),
    can_confirm: z.boolean(),
    // O backend diz se este usuário tem a permissão de enviar ao ERP.
    can_send: z.boolean(),
})

export type { ErpState }
export type ErpSummary = z.infer<typeof erpSummarySchema>
export type ErpDetail = z.infer<typeof erpDetailSchema>
