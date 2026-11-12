import { useState } from 'react'
import { Link2Off } from 'lucide-react'
import { Alert, ConfirmDialog, EmptyState, Pagination } from '../../../shared/components'
import { useAuth } from '../../auth'
import { usePaymentDecision, usePaymentProcesses } from '../hooks'
import { PROCESS_STATUSES, type Decision, type PaymentProcess, type ProcessStatus } from '../schemas/payments'
import { PAGE_SIZE } from '../services/payments.service'
import { STATUS_LABELS } from '../utils'
import { ProcessCard } from './ProcessCard'

/** Revisão dos agrupamentos de nota fiscal e boletos: nada vira processo sem a confirmação do operador. */
export function PaymentsView() {
    const { hasPermission } = useAuth()
    const canDecide = hasPermission('documents.validate')
    const [status, setStatus] = useState<ProcessStatus>('PENDING')
    const [page, setPage] = useState(1)
    const [rejecting, setRejecting] = useState<PaymentProcess | null>(null)
    const [notice, setNotice] = useState('')
    const query = usePaymentProcesses(status, page)
    const { decide, busy, error, reset } = usePaymentDecision()

    const choose = (next: ProcessStatus) => {
        setStatus(next)
        setPage(1)
        setNotice('')
        reset()
    }
    const submit = async (process: PaymentProcess, decision: Decision) => {
        setNotice('')
        try {
            await decide({ processId: process.id, decision })
            setNotice(decision === 'confirm' ? 'Processo de pagamento confirmado.' : 'Agrupamento rejeitado.')
        } catch {
            // O hook já expõe a mensagem em `error`.
        }
    }
    const onDecide = (process: PaymentProcess, decision: Decision) =>
        decision === 'reject' ? setRejecting(process) : void submit(process, decision)

    const results = query.data?.results ?? []
    return (
        <section className="mx-auto w-full max-w-4xl px-4 py-6">
            <h1 className="text-lg font-semibold text-zinc-900">Pagamentos</h1>
            <p className="mb-4 text-sm text-zinc-500">
                Notas fiscais e os boletos que as pagam. Confirme ou rejeite cada agrupamento.
            </p>
            <div role="tablist" aria-label="Situação" className="mb-4 flex gap-1 border-b border-zinc-200">
                {PROCESS_STATUSES.map((value) => (
                    <button
                        key={value}
                        type="button"
                        role="tab"
                        aria-selected={status === value}
                        onClick={() => choose(value)}
                        className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                            status === value
                                ? 'border-zinc-900 text-zinc-900'
                                : 'border-transparent text-zinc-500 hover:text-zinc-800'
                        }`}
                    >
                        {STATUS_LABELS[value]}
                    </button>
                ))}
            </div>
            {notice ? <Alert tone="success">{notice}</Alert> : null}
            {error ? <Alert tone="error">{error}</Alert> : null}
            {query.isError ? <Alert tone="error">Não foi possível carregar os processos de pagamento.</Alert> : null}
            {query.isLoading ? <p className="text-sm text-zinc-500">Carregando…</p> : null}
            {!query.isLoading && !query.isError && results.length === 0 ? (
                <EmptyState icon={Link2Off} text="Nenhum processo de pagamento nesta situação." />
            ) : null}
            <div className="flex flex-col gap-3">
                {results.map((process) => (
                    <ProcessCard
                        key={process.id}
                        process={process}
                        canDecide={canDecide}
                        busy={busy}
                        onDecide={onDecide}
                    />
                ))}
            </div>
            <Pagination
                page={page}
                totalPages={query.data?.total_pages ?? 1}
                count={query.data?.count ?? 0}
                pageSize={PAGE_SIZE}
                unit={['processo', 'processos']}
                onPageChange={setPage}
            />
            {rejecting ? (
                <ConfirmDialog
                    title="Rejeitar agrupamento?"
                    message="A nota e os boletos voltam para os documentos sem match e este par não será sugerido de novo."
                    confirmLabel="Rejeitar"
                    onCancel={() => setRejecting(null)}
                    onConfirm={async () => {
                        const target = rejecting
                        setRejecting(null)
                        await submit(target, 'reject')
                    }}
                />
            ) : null}
        </section>
    )
}
