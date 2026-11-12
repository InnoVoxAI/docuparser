import { useState } from 'react'
import { Alert } from '../../../shared/components'
import { PROCESS_STATUSES, type ProcessStatus } from '../schemas/payments'
import { STATUS_LABELS } from '../utils'
import { ProcessList } from './ProcessList'
import { UnmatchedPanel } from './UnmatchedPanel'

type Tab = ProcessStatus | 'UNMATCHED'

const TABS: { value: Tab; label: string }[] = [
    ...PROCESS_STATUSES.map((value) => ({ value, label: STATUS_LABELS[value] })),
    { value: 'UNMATCHED', label: 'Sem match' },
]

/** Pagamentos: revisão dos agrupamentos de nota e boletos e o pareamento manual dos sem match. */
export function PaymentsView() {
    const [tab, setTab] = useState<Tab>('PENDING')
    const [notice, setNotice] = useState('')

    const choose = (next: Tab) => {
        setTab(next)
        setNotice('')
    }
    return (
        <section className="mx-auto w-full max-w-5xl px-4 py-6">
            <h1 className="text-lg font-semibold text-zinc-900">Pagamentos</h1>
            <p className="mb-4 text-sm text-zinc-500">
                Notas fiscais e os boletos que as pagam. Nada vira processo de pagamento sem a sua confirmação.
            </p>
            <div role="tablist" aria-label="Situação" className="mb-4 flex flex-wrap gap-1 border-b border-zinc-200">
                {TABS.map(({ value, label }) => (
                    <button
                        key={value}
                        type="button"
                        role="tab"
                        aria-selected={tab === value}
                        onClick={() => choose(value)}
                        className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                            tab === value
                                ? 'border-zinc-900 text-zinc-900'
                                : 'border-transparent text-zinc-500 hover:text-zinc-800'
                        }`}
                    >
                        {label}
                    </button>
                ))}
            </div>
            {notice ? <Alert tone="success">{notice}</Alert> : null}
            {tab === 'UNMATCHED' ? (
                <UnmatchedPanel
                    onCreated={() => {
                        setTab('PENDING')
                        setNotice('Agrupamento montado. Confirme-o aqui, ou desfaça a seleção.')
                    }}
                />
            ) : (
                <ProcessList key={tab} status={tab} onNotice={setNotice} />
            )}
        </section>
    )
}
