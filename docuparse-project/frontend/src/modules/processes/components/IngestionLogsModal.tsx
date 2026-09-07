import { X } from 'lucide-react'
import { useBodyScrollLock } from '../../../shared/hooks'
import type { ProcessPipeline, StepExecution } from '../types'

function formatDateTime(value: string): string {
    return new Date(value).toLocaleString('pt-BR')
}

interface LogRow extends StepExecution {
    stepLabel: string
}

function collectLogs(pipeline: ProcessPipeline): LogRow[] {
    const rows: LogRow[] = []
    for (const step of pipeline.steps) {
        if (step.key !== 'ocr' && step.key !== 'extraction') continue
        for (const execution of step.executions) {
            rows.push({ ...execution, stepLabel: step.label })
        }
    }
    return rows.sort((a, b) => b.created_at.localeCompare(a.created_at))
}

/** Popup só-leitura com o histórico técnico da Ingestão — aberto ao clicar na
 * caixa "Ingestão" quando ela está em erro. */
export function IngestionLogsModal({ pipeline, onClose }: { pipeline: ProcessPipeline; onClose: () => void }) {
    useBodyScrollLock()
    const logs = collectLogs(pipeline)

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            onClick={(event) => {
                if (event.target === event.currentTarget) onClose()
            }}
            onKeyDown={(event) => {
                if (event.key === 'Escape') onClose()
            }}
            role="button"
            tabIndex={0}
            aria-label="Fechar logs"
        >
            <div
                className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-xl bg-white p-6 shadow-lg"
                role="dialog"
                aria-modal="true"
                aria-label="Logs da ingestão"
            >
                <div className="mb-4 flex flex-shrink-0 items-start justify-between">
                    <div>
                        <h3 className="text-base font-semibold text-zinc-900">Logs da ingestão</h3>
                        <p className="mt-0.5 text-xs text-zinc-500">{pipeline.original_filename}</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Fechar"
                        className="text-zinc-400 hover:text-zinc-700"
                    >
                        <X size={20} aria-hidden="true" />
                    </button>
                </div>

                {logs.length === 0 ? (
                    <p className="text-sm text-zinc-500">Nenhum registro de execução disponível.</p>
                ) : (
                    <ul className="flex-1 space-y-2 overflow-auto">
                        {logs.map((log) => (
                            <li
                                key={log.task_id}
                                className={`rounded-md border p-3 text-sm ${
                                    log.status === 'ERROR'
                                        ? 'border-red-200 bg-red-50'
                                        : 'border-emerald-200 bg-emerald-50'
                                }`}
                            >
                                <div className="flex items-center justify-between font-medium text-zinc-800">
                                    <span>
                                        {log.stepLabel} — tentativa {log.attempt} (
                                        {log.status === 'OK' ? 'sucesso' : 'erro'})
                                    </span>
                                    <span className="text-xs font-normal text-zinc-500">
                                        {formatDateTime(log.created_at)}
                                    </span>
                                </div>
                                {log.error_message ? (
                                    <pre className="mt-2 overflow-auto whitespace-pre-wrap rounded bg-zinc-950 p-3 text-xs text-zinc-50">
                                        {log.error_type ? `${log.error_type}: ` : ''}
                                        {log.error_message}
                                    </pre>
                                ) : (
                                    <p className="mt-1 text-xs text-zinc-500">Concluída sem erros.</p>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    )
}
