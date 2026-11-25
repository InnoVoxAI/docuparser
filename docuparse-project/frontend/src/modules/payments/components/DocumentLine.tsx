import { formatDate } from '../../../shared/utils'
import type { PaymentDocument } from '../schemas/payments'
import { describeOrigin, formatCnpj, formatMoney } from '../utils'

interface Props {
    kind: 'Nota fiscal' | 'Boleto'
    doc: PaymentDocument
    /** Abre o popup com os documentos lado a lado. */
    onOpen?: () => void
}

/** Uma linha do processo: nota ou boleto, com o CNPJ e o valor usados no casamento. */
export function DocumentLine({ kind, doc, onOpen }: Props) {
    const name = doc.original_filename || 'Sem nome'
    return (
        <li className="grid gap-1 py-2 text-sm sm:grid-cols-[6rem_1fr_auto] sm:items-baseline sm:gap-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{kind}</span>
            <div className="min-w-0">
                {onOpen ? (
                    <button
                        type="button"
                        onClick={onOpen}
                        title={`Ver ${name} lado a lado`}
                        className="block max-w-full truncate text-left font-medium text-zinc-900 underline-offset-2 hover:underline"
                    >
                        {name}
                    </button>
                ) : (
                    <div className="truncate font-medium text-zinc-900" title={name}>
                        {name}
                    </div>
                )}
                <div className="text-xs text-zinc-500">
                    {formatCnpj(doc.tax_id)} · {describeOrigin(doc)} · {formatDate(doc.received_at)}
                </div>
            </div>
            <span className="font-semibold tabular-nums text-zinc-900">{formatMoney(doc.amount)}</span>
        </li>
    )
}
