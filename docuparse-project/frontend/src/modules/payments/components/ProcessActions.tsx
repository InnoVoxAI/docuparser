import { Check, Undo2, X } from 'lucide-react'
import type { Decision, PaymentProcess } from '../schemas/payments'

interface Props {
    process: PaymentProcess
    canDecide: boolean
    busy: boolean
    onDecide: (process: PaymentProcess, decision: Decision) => void
    onUndo: (process: PaymentProcess) => void
}

const SECONDARY =
    'inline-flex h-9 items-center gap-1 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50'

/** Confirmar e rejeitar (ou desfazer a seleção manual) de um agrupamento ainda pendente. */
export function ProcessActions({ process, canDecide, busy, onDecide, onUndo }: Props) {
    if (process.status !== 'PENDING' || !canDecide) return null
    return (
        <div className="flex gap-2">
            {process.origin === 'MANUAL' ? (
                <button type="button" disabled={busy} onClick={() => onUndo(process)} className={SECONDARY}>
                    <Undo2 size={16} aria-hidden="true" /> Desfazer seleção
                </button>
            ) : (
                <button type="button" disabled={busy} onClick={() => onDecide(process, 'reject')} className={SECONDARY}>
                    <X size={16} aria-hidden="true" /> Rejeitar
                </button>
            )}
            <button
                type="button"
                disabled={busy}
                onClick={() => onDecide(process, 'confirm')}
                className="inline-flex h-9 items-center gap-1 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
            >
                <Check size={16} aria-hidden="true" /> Confirmar
            </button>
        </div>
    )
}
