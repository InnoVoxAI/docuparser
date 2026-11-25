export { ERP_STATE_LABELS, erpStateTone } from '../../shared/utils'

/** "1000.00" vira "R$ 1.000,00". */
export function formatMoney(value: string): string {
    const amount = Number(value)
    return Number.isFinite(amount)
        ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(amount)
        : value
}

/** "2026-07-20" vira "20/07/2026", sem passar por fuso horário. */
export function formatIsoDate(value: string): string {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
    return match ? `${match[3]}/${match[2]}/${match[1]}` : value
}

/** Hora local de um instante ISO, para dizer quando o reenvio fica liberado. */
export function formatClock(value: string): string {
    const date = new Date(value)
    return Number.isNaN(date.getTime())
        ? ''
        : new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(date)
}
