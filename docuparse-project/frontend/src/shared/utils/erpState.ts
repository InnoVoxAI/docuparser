/** Estados do lançamento da despesa no ERP, compartilhados entre as telas que o mostram. */
export const ERP_STATES = ['none', 'awaiting_confirmation', 'blocked', 'sending', 'sent', 'failed', 'dry_run'] as const

export type ErpState = (typeof ERP_STATES)[number]

export const ERP_STATE_LABELS: Record<ErpState, string> = {
    none: 'Sem lançamento',
    awaiting_confirmation: 'Aguardando confirmação',
    blocked: 'Com pendências',
    sending: 'Enviando',
    sent: 'Enviado ao ERP',
    failed: 'Falha no envio',
    dry_run: 'Simulação',
}

const STATE_TONES: Record<ErpState, string> = {
    none: 'bg-zinc-100 text-zinc-600',
    awaiting_confirmation: 'bg-amber-100 text-amber-800',
    blocked: 'bg-amber-100 text-amber-800',
    sending: 'bg-blue-100 text-blue-800',
    sent: 'bg-emerald-100 text-emerald-800',
    failed: 'bg-red-100 text-red-800',
    dry_run: 'bg-zinc-100 text-zinc-700',
}

export function erpStateTone(state: ErpState): string {
    return STATE_TONES[state]
}
