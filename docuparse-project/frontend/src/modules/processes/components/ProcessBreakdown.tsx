import { AlertTriangle, Check, ChevronRight, Clock, Loader2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ProcessPipeline, ProcessStep, StepKey } from '../types'

type BoxState = 'pending' | 'current' | 'done' | 'error' | 'rejected'

interface BoxModel {
    key: 'queue' | 'ingestion' | 'validation' | 'classification'
    label: string
    state: BoxState
    /** Caixa clicável? Só "Ingestão" em erro e "Validação" aguardando ação. */
    action: 'logs' | 'validate' | null
    hint: string
}

const STATE_STYLES: Record<BoxState, string> = {
    pending: 'border-zinc-200 bg-zinc-50 text-zinc-400',
    current: 'border-sky-300 bg-sky-50 text-sky-800',
    done: 'border-emerald-300 bg-emerald-50 text-emerald-800',
    error: 'border-red-300 bg-red-50 text-red-800',
    rejected: 'border-red-300 bg-red-50 text-red-800',
}

const STATE_ICON: Record<BoxState, LucideIcon> = {
    pending: Clock,
    current: Loader2,
    done: Check,
    error: AlertTriangle,
    rejected: AlertTriangle,
}

const STATE_TEXT: Record<BoxState, string> = {
    pending: 'Aguardando',
    current: 'Em andamento',
    done: 'Concluído',
    error: 'Erro',
    rejected: 'Rejeitado',
}

function stepByKey(steps: ProcessStep[]): Record<StepKey, ProcessStep | undefined> {
    return steps.reduce(
        (acc, step) => {
            acc[step.key] = step
            return acc
        },
        {} as Record<StepKey, ProcessStep | undefined>,
    )
}

/** Traduz os steps técnicos do pipeline nas 4 caixas de negócio da Visão Geral:
 * Em fila → Ingestão → Validação → Classificação. */
function deriveBoxes(pipeline: ProcessPipeline): BoxModel[] {
    const byKey = stepByKey(pipeline.steps)
    const ocr = byKey.ocr
    const extraction = byKey.extraction
    const validation = byKey.validation_decision
    const classification = byKey.classification

    const ingestionStarted = Boolean(ocr && (ocr.status !== 'PENDING' || ocr.executions.length > 0))
    const ingestionError = ocr?.status === 'ERROR' || extraction?.status === 'ERROR'
    const ingestionDone = ocr?.status === 'OK' && extraction?.status === 'OK'

    const queue: BoxModel = {
        key: 'queue',
        label: 'Em fila',
        state: ingestionStarted ? 'done' : 'current',
        action: null,
        hint: ingestionStarted ? 'Processo já retirado da fila.' : 'Processo aguardando início do processamento.',
    }

    let ingestionState: BoxState = 'pending'
    if (ingestionError) ingestionState = 'error'
    else if (ingestionDone) ingestionState = 'done'
    else if (ingestionStarted) ingestionState = 'current'
    const ingestion: BoxModel = {
        key: 'ingestion',
        label: 'Ingestão',
        state: ingestionState,
        action: ingestionError ? 'logs' : null,
        hint: ingestionError
            ? 'Ocorreu um erro durante o processamento. Clique para ver os detalhes.'
            : 'Leitura e interpretação do documento.',
    }

    let validationState: BoxState = 'pending'
    if (validation?.status === 'OK') validationState = 'done'
    else if (validation?.status === 'REJECTED') validationState = 'rejected'
    else if (validation?.status === 'PENDING' && ingestionDone) validationState = 'current'
    const validation_box: BoxModel = {
        key: 'validation',
        label: 'Validação',
        state: validationState,
        action: validationState === 'current' ? 'validate' : null,
        hint:
            validationState === 'current'
                ? 'Aguardando validação humana. Clique para revisar os campos.'
                : validationState === 'rejected'
                  ? 'Processo rejeitado na validação.'
                  : 'Conferência humana dos dados extraídos.',
    }

    let classificationState: BoxState = 'pending'
    if (classification?.status === 'OK') classificationState = 'done'
    else if (classification?.status === 'ERROR') classificationState = 'error'
    else if (validation?.status === 'OK') classificationState = 'current'
    const classification_box: BoxModel = {
        key: 'classification',
        label: 'Classificação',
        state: classificationState,
        action: null,
        hint: 'Classificação e encaminhamento do processo (segue fora da plataforma).',
    }

    return [queue, ingestion, validation_box, classification_box]
}

function Box({
    box,
    onOpenLogs,
    onOpenValidation,
}: {
    box: BoxModel
    onOpenLogs: () => void
    onOpenValidation: () => void
}) {
    const Icon = STATE_ICON[box.state]
    const className = `flex w-full flex-col gap-1 rounded-lg border px-4 py-3 text-left ${STATE_STYLES[box.state]}`
    const body = (
        <>
            <span className="flex items-center gap-1.5 text-sm font-semibold">
                <Icon size={15} aria-hidden="true" className={box.state === 'current' ? 'animate-spin' : ''} />
                {box.label}
            </span>
            <span className="text-xs font-medium opacity-80">{STATE_TEXT[box.state]}</span>
        </>
    )

    if (box.action === 'logs') {
        return (
            <button type="button" onClick={onOpenLogs} className={`${className} hover:brightness-95`} title={box.hint}>
                {body}
                <span className="mt-0.5 text-xs font-normal opacity-70">Ver logs do erro</span>
            </button>
        )
    }
    if (box.action === 'validate') {
        return (
            <button
                type="button"
                onClick={onOpenValidation}
                className={`${className} hover:brightness-95`}
                title={box.hint}
            >
                {body}
                <span className="mt-0.5 text-xs font-normal opacity-70">Revisar e decidir</span>
            </button>
        )
    }
    return (
        <div className={className} title={box.hint} aria-label={`${box.label}: ${STATE_TEXT[box.state]}`}>
            {body}
        </div>
    )
}

export function ProcessBreakdown({
    pipeline,
    onOpenLogs,
    onOpenValidation,
}: {
    pipeline: ProcessPipeline
    onOpenLogs: () => void
    onOpenValidation: () => void
}) {
    const boxes = deriveBoxes(pipeline)
    return (
        <ol className="flex flex-col gap-2 sm:flex-row sm:items-stretch" aria-label="Etapas do processo">
            {boxes.map((box, index) => (
                <li key={box.key} className="flex flex-1 items-center gap-2">
                    <div className="flex-1">
                        <Box box={box} onOpenLogs={onOpenLogs} onOpenValidation={onOpenValidation} />
                    </div>
                    {index < boxes.length - 1 ? (
                        <ChevronRight size={16} aria-hidden="true" className="hidden shrink-0 text-zinc-300 sm:block" />
                    ) : null}
                </li>
            ))}
        </ol>
    )
}
