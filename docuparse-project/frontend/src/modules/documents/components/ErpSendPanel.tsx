import { useState } from 'react'
import { Alert } from '../../../shared/components'
import { ERP_STATE_LABELS, erpStateTone, formatClock } from '../erp'
import { useErpActions, useErpDetail } from '../hooks/useErp'
import type { ErpDetail } from '../schemas/erp'
import { ErpConfirmDialog } from './ErpConfirmDialog'
import { ErpSummary } from './ErpSummary'

function RetryHint({ detail }: { detail: ErpDetail }) {
    if (detail.exhausted) return <p className="text-xs text-red-700">As tentativas se esgotaram. Procure o suporte.</p>
    const when = detail.next_retry_at ? formatClock(detail.next_retry_at) : ''
    return (
        <p className="text-xs text-zinc-500">
            Tentativa {detail.attempts} de {detail.max_attempts}
            {!detail.can_retry && when ? `. Disponível de novo às ${when}.` : '.'}
        </p>
    )
}

/**
 * Lançamento da despesa no ERP. O analista vê o resumo, confirma o envio e, se a
 * falha for passageira, tenta de novo. Só aparece quando há algo a mostrar.
 */
export function ErpSendPanel({
    documentId,
    onChanged,
}: {
    documentId: string
    onChanged?: () => void | Promise<unknown>
}) {
    const query = useErpDetail(documentId)
    const actions = useErpActions(documentId, onChanged)
    const [confirming, setConfirming] = useState(false)
    const detail = query.data
    if (!detail || detail.state === 'none') return null

    const submit = async () => {
        // Se a API recusar, o diálogo continua aberto mostrando o motivo.
        if (await actions.confirm()) setConfirming(false)
    }
    return (
        <section aria-label="Lançamento no ERP" className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                <span className="text-sm font-semibold">Lançamento no ERP</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${erpStateTone(detail.state)}`}>
                    {ERP_STATE_LABELS[detail.state]}
                </span>
            </div>
            <div className="space-y-3 p-3">
                {detail.state === 'blocked' ? (
                    <Alert tone="error">
                        <strong>Corrija antes de enviar:</strong>
                        <ul className="mt-1 list-disc pl-5">
                            {detail.errors.map((issue) => (
                                <li key={issue.code + issue.message}>{issue.message}</li>
                            ))}
                        </ul>
                    </Alert>
                ) : null}
                {detail.summary ? <ErpSummary summary={detail.summary} /> : null}
                {detail.state === 'sending' ? <p className="text-sm text-zinc-600">Enviando ao ERP...</p> : null}
                {detail.state === 'sent' ? (
                    <p className="text-sm text-emerald-800">Despesa lançada no ERP (id {detail.external_id}).</p>
                ) : null}
                {detail.state === 'dry_run' ? (
                    <p className="text-sm text-zinc-600">Simulação concluída: nada foi enviado ao ERP.</p>
                ) : null}
                {detail.state === 'failed' ? (
                    <>
                        <Alert tone="error">{detail.reason}</Alert>
                        {detail.retryable ? (
                            <RetryHint detail={detail} />
                        ) : (
                            <p className="text-xs text-zinc-500">Corrija o documento e envie de novo.</p>
                        )}
                    </>
                ) : null}
                {actions.error && !confirming ? <Alert tone="error">{actions.error}</Alert> : null}
                {detail.can_send ? (
                    <div className="flex gap-2">
                        {detail.can_confirm ? (
                            <button type="button" className="primary-button" onClick={() => setConfirming(true)}>
                                {detail.dry_run ? 'Simular envio' : 'Enviar ao ERP'}
                            </button>
                        ) : null}
                        {detail.state === 'failed' && detail.retryable ? (
                            <button
                                type="button"
                                className="primary-button"
                                disabled={!detail.can_retry || actions.busy}
                                onClick={() => actions.retry()}
                            >
                                Tentar de novo
                            </button>
                        ) : null}
                    </div>
                ) : null}
            </div>
            {confirming && detail.summary ? (
                <ErpConfirmDialog
                    summary={detail.summary}
                    dryRun={detail.dry_run}
                    busy={actions.busy}
                    error={actions.error}
                    onConfirm={submit}
                    onCancel={() => {
                        actions.reset()
                        setConfirming(false)
                    }}
                />
            ) : null}
        </section>
    )
}
