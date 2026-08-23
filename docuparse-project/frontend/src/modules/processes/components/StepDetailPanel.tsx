import { Alert, EmptyState } from '../../../shared/components'
import { MousePointerClick } from 'lucide-react'
import type { ProcessStep } from '../types'

function formatDateTime(value: string): string {
    return new Date(value).toLocaleString('pt-BR')
}

function triggerLabel(triggeredBy: string | null): string {
    return triggeredBy ? `Manual — ${triggeredBy}` : 'Automático'
}

export function StepDetailPanel({
    step,
    onRetry,
    retrying,
    retryError,
}: {
    step: ProcessStep | null
    onRetry: () => void
    retrying: boolean
    retryError: string
}) {
    if (!step) {
        return (
            <EmptyState icon={MousePointerClick} text="Selecione uma etapa no diagrama pra ver o detalhe." />
        )
    }

    return (
        <div className="space-y-4 p-4">
            {retryError ? <Alert tone="error">{retryError}</Alert> : null}
            <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-zinc-800">{step.label}</h3>
                {step.retryable ? (
                    <button
                        type="button"
                        onClick={onRetry}
                        disabled={retrying}
                        className="inline-flex h-8 items-center rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {retrying ? 'Tentando novamente...' : 'Tentar novamente'}
                    </button>
                ) : null}
            </div>

            {step.executions.length === 0 ? (
                <p className="text-sm text-zinc-500">Nenhuma execução registrada ainda.</p>
            ) : (
                <ul className="space-y-2">
                    {step.executions.map((execution) => (
                        <li
                            key={execution.task_id}
                            className={`rounded-md border p-3 text-sm ${
                                execution.status === 'ERROR'
                                    ? 'border-red-200 bg-red-50'
                                    : 'border-emerald-200 bg-emerald-50'
                            }`}
                        >
                            <div className="flex items-center justify-between font-medium">
                                <span>
                                    Tentativa {execution.attempt} — {execution.status === 'OK' ? 'sucesso' : 'erro'}
                                </span>
                                <span className="text-xs font-normal text-zinc-500">
                                    {formatDateTime(execution.created_at)}
                                </span>
                            </div>
                            <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                                <span>Duração: {execution.duration_ms}ms</span>
                                <span aria-hidden="true">·</span>
                                <span
                                    className={
                                        execution.triggered_by
                                            ? 'font-medium text-zinc-700'
                                            : undefined
                                    }
                                >
                                    {triggerLabel(execution.triggered_by)}
                                </span>
                            </div>
                            {execution.error_message ? (
                                <div className="mt-2 rounded bg-white/60 p-2 font-mono text-xs text-red-700">
                                    {execution.error_type}: {execution.error_message}
                                </div>
                            ) : null}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
