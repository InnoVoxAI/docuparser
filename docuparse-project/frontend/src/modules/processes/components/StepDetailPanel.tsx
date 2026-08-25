import { Alert, EmptyState } from '../../../shared/components'
import { ExternalLink, MousePointerClick } from 'lucide-react'
import type { ProcessStep } from '../types'

function formatDateTime(value: string): string {
    return new Date(value).toLocaleString('pt-BR')
}

function triggerLabel(triggeredBy: string | null): string {
    return triggeredBy ? `Manual — ${triggeredBy}` : 'Automático'
}

const PAYLOAD_LABELS: Record<string, string> = {
    document_type: 'Tipo de documento',
    raw_text_uri: 'Texto (referência de armazenamento)',
    schema_id: 'Schema',
    confidence: 'Confiança',
    fields: 'Campos extraídos',
    decision: 'Decisão',
    corrected_fields: 'Campos corrigidos',
}

const DECISION_LABELS: Record<string, string> = {
    approved: 'Aprovado',
    rejected: 'Rejeitado',
    corrected: 'Corrigido',
}

function isEmptyValue(value: unknown): boolean {
    if (value === null || value === undefined || value === '') return true
    if (typeof value === 'object') return Object.keys(value).length === 0
    return false
}

function formatScalarValue(key: string, value: unknown): string {
    if (key === 'decision' && typeof value === 'string') return DECISION_LABELS[value] ?? value
    return String(value)
}

/** Um campo extraído (fields/corrected_fields) vem como `{value, confidence}`
 * ou como escalar puro — mesmo formato dual de `ExtractionResult.fields`
 * (ver `modules/documents/utils.ts`'s `parseFieldEntry`, não reusado aqui
 * pra manter este módulo sem depender de outro módulo de domínio). Sem
 * isso, o objeto `{value, confidence}` vira o inútil "[object Object]". */
function formatFieldValue(raw: unknown): string {
    if (raw === null || raw === undefined) return ''
    if (typeof raw === 'object' && 'value' in raw) {
        const value = (raw as { value?: unknown }).value
        return value === null || value === undefined ? '' : String(value)
    }
    return String(raw)
}

/** Saída de uma tentativa — `notes` (motivo de rejeição/observação da
 * validação) ganha destaque próprio, o resto vira uma lista chave:valor
 * genérica (objetos aninhados, como `fields`, viram uma sub-lista). */
function PayloadOutput({ payload }: { payload: Record<string, unknown> }) {
    const notes = typeof payload.notes === 'string' ? payload.notes : ''
    const entries = Object.entries(payload).filter(([key, value]) => key !== 'notes' && !isEmptyValue(value))

    if (!notes && entries.length === 0) return null

    return (
        <div className="mt-2 space-y-2">
            {notes ? (
                <div className="rounded bg-white/70 p-2 text-xs text-zinc-700">
                    <span className="font-medium">Motivo: </span>
                    {notes}
                </div>
            ) : null}
            {entries.length > 0 ? (
                <dl className="space-y-1 text-xs text-zinc-600">
                    {entries.map(([key, value]) => (
                        <div key={key} className="flex gap-1">
                            <dt className="shrink-0 font-medium text-zinc-700">{PAYLOAD_LABELS[key] ?? key}:</dt>
                            <dd className="min-w-0 break-words">
                                {typeof value === 'object' && value !== null ? (
                                    <ul>
                                        {Object.entries(value as Record<string, unknown>).map(([field, fieldValue]) => (
                                            <li key={field}>
                                                <span className="font-medium">{field}:</span>{' '}
                                                {formatFieldValue(fieldValue)}
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    formatScalarValue(key, value)
                                )}
                            </dd>
                        </div>
                    ))}
                </dl>
            ) : null}
        </div>
    )
}

export function StepDetailPanel({
    step,
    onRetry,
    retrying,
    retryError,
    onGoToValidation,
}: {
    step: ProcessStep | null
    onRetry: () => void
    retrying: boolean
    retryError: string
    onGoToValidation: () => void
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
                {step.key === 'validation_decision' ? (
                    <button
                        type="button"
                        onClick={onGoToValidation}
                        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        Revisar na tela de validação
                        <ExternalLink size={14} aria-hidden="true" />
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
                            <PayloadOutput payload={execution.payload} />
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
