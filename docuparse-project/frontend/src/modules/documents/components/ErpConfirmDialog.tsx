import { Alert } from '../../../shared/components'
import type { ErpSummary as ErpSummaryData } from '../schemas/erp'
import { ErpSummary } from './ErpSummary'

/** Confirmação antes de lançar no ERP: mostra o resumo e deixa claro o que acontece. */
export function ErpConfirmDialog({
    summary,
    dryRun,
    busy,
    error,
    onConfirm,
    onCancel,
}: {
    summary: ErpSummaryData
    dryRun: boolean
    busy: boolean
    error: string
    onConfirm: () => void | Promise<unknown>
    onCancel: () => void
}) {
    const title = dryRun ? 'Simular o envio ao ERP?' : 'Enviar esta despesa ao ERP?'
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            aria-label={title}
        >
            <div className="w-full max-w-md rounded-md border border-zinc-200 bg-white p-4 shadow-lg">
                <div className="text-sm font-semibold text-zinc-900">{title}</div>
                <p className="mt-1 mb-3 text-sm text-zinc-600">
                    {dryRun
                        ? 'Nada será enviado: o sistema só monta e valida a despesa abaixo.'
                        : 'A despesa abaixo será lançada no ERP e não pode ser desfeita por aqui.'}
                </p>
                <ErpSummary summary={summary} />
                {error ? <Alert tone="error">{error}</Alert> : null}
                <div className="mt-4 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        disabled={busy}
                        onClick={onConfirm}
                        className="h-9 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {dryRun ? 'Simular' : 'Enviar ao ERP'}
                    </button>
                </div>
            </div>
        </div>
    )
}
