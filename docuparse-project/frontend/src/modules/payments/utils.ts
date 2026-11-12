import type { PaymentDocument, ProcessStatus } from './schemas/payments'

export const STATUS_LABELS: Record<ProcessStatus, string> = {
    PENDING: 'Para revisar',
    CONFIRMED: 'Confirmados',
    REJECTED: 'Rejeitados',
}

export const ORIGIN_LABELS = { AUTOMATIC: 'Sugerido pelo sistema', MANUAL: 'Montado à mão' } as const

const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function formatMoney(amount: string | null): string {
    return amount === null ? 'valor não lido' : BRL.format(Number(amount))
}

export function formatCnpj(taxId: string | null): string {
    if (!taxId) return 'CNPJ não lido'
    return /^\d{14}$/.test(taxId) ? taxId.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5') : taxId
}

/** De onde o documento veio: o e-mail ou a conversa de WhatsApp, quando o canal sabe. */
export function describeOrigin(doc: PaymentDocument): string {
    if (doc.source_thread_id.startsWith('whatsapp:')) return `WhatsApp ${doc.source_thread_id.slice(9)}`
    if (doc.source_thread_id.startsWith('email:')) return 'E-mail'
    return doc.channel === 'manual' ? 'Envio manual' : doc.channel
}

/** Quanto da nota os boletos cobrem, para o operador ver parcelas faltando ou sobrando. */
export function describeCoverage(invoiceAmount: string | null, boletosTotal: string | null): string {
    if (invoiceAmount === null || boletosTotal === null) return ''
    const diff = Number(invoiceAmount) - Number(boletosTotal)
    if (Math.abs(diff) < 0.005) return 'Os boletos cobrem a nota inteira.'
    return diff > 0
        ? `Faltam ${formatMoney(diff.toFixed(2))} para cobrir a nota.`
        : `Os boletos passam da nota em ${formatMoney((-diff).toFixed(2))}.`
}
