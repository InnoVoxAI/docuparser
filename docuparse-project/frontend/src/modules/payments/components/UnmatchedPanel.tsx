import { useState } from 'react'
import { useAuth } from '../../auth'
import { useManualMatch } from '../hooks'
import type { PaymentDocument } from '../schemas/payments'
import { CandidateList } from './CandidateList'
import { SelectionBar } from './SelectionBar'

/** Documentos sem match: o operador escolhe a nota e os boletos e monta o agrupamento à mão. */
export function UnmatchedPanel({ onCreated }: { onCreated: () => void }) {
    const { hasPermission } = useAuth()
    const canDecide = hasPermission('documents.validate')
    const [invoice, setInvoice] = useState<PaymentDocument | null>(null)
    const [boletos, setBoletos] = useState<PaymentDocument[]>([])
    const { create, busy, error, reset } = useManualMatch()

    const toggleBoleto = (doc: PaymentDocument) =>
        setBoletos((current) =>
            current.some((b) => b.id === doc.id) ? current.filter((b) => b.id !== doc.id) : [...current, doc],
        )
    const clear = () => {
        setInvoice(null)
        setBoletos([])
        reset()
    }
    const submit = async () => {
        if (!invoice) return
        try {
            await create({ invoiceId: invoice.id, boletoIds: boletos.map((b) => b.id) })
            clear()
            onCreated()
        } catch {
            // O hook já expõe a mensagem em `error`.
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <p className="text-sm text-zinc-500">
                Documentos que não fazem parte de nenhum agrupamento. Os que estão em um agrupamento aguardando revisão
                só voltam aqui se esse agrupamento for rejeitado.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
                <CandidateList
                    kind="invoice"
                    title="Notas fiscais"
                    selected={invoice ? [invoice] : []}
                    onToggle={setInvoice}
                />
                <CandidateList kind="boleto" title="Boletos" selected={boletos} onToggle={toggleBoleto} />
            </div>
            {canDecide ? (
                <SelectionBar
                    invoice={invoice}
                    boletos={boletos}
                    busy={busy}
                    error={error}
                    onClear={clear}
                    onCreate={() => void submit()}
                />
            ) : null}
        </div>
    )
}
