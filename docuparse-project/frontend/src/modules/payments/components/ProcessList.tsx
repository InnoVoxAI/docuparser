import { useState } from 'react'
import { Link2Off } from 'lucide-react'
import { Alert, ConfirmDialog, EmptyState, Pagination } from '../../../shared/components'
import { useAuth } from '../../auth'
import { useManualMatch, usePaymentDecision, usePaymentProcesses } from '../hooks'
import type { Decision, PaymentProcess, ProcessStatus } from '../schemas/payments'
import { PAGE_SIZE } from '../services/payments.service'
import { ProcessCard } from './ProcessCard'

/** Agrupamentos de uma situação, com confirmar, rejeitar e desfazer a seleção manual. */
export function ProcessList({ status, onNotice }: { status: ProcessStatus; onNotice: (text: string) => void }) {
    const { hasPermission } = useAuth()
    const canDecide = hasPermission('documents.validate')
    const [page, setPage] = useState(1)
    const [rejecting, setRejecting] = useState<PaymentProcess | null>(null)
    const query = usePaymentProcesses(status, page)
    const decision = usePaymentDecision()
    const manual = useManualMatch()

    const submit = async (process: PaymentProcess, action: Decision) => {
        onNotice('')
        try {
            await decision.decide({ processId: process.id, decision: action })
            onNotice(action === 'confirm' ? 'Processo de pagamento confirmado.' : 'Agrupamento rejeitado.')
        } catch {
            // O hook já expõe a mensagem em `decision.error`.
        }
    }
    const undo = async (process: PaymentProcess) => {
        onNotice('')
        try {
            await manual.undo(process.id)
            onNotice('Seleção desfeita: os documentos voltaram para a lista de sem match.')
        } catch {
            // O hook já expõe a mensagem em `manual.error`.
        }
    }

    const results = query.data?.results ?? []
    const error = decision.error || manual.error
    return (
        <>
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
                        busy={decision.busy || manual.busy}
                        onDecide={(target, action) =>
                            action === 'reject' ? setRejecting(target) : void submit(target, action)
                        }
                        onUndo={(target) => void undo(target)}
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
        </>
    )
}
