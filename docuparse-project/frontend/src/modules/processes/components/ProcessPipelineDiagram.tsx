import type { ProcessStep, StepKey } from '../types'

const BOX_STYLES: Record<string, string> = {
    OK: 'border-emerald-500 bg-emerald-50 text-emerald-700',
    ERROR: 'border-red-500 bg-red-50 text-red-700',
    PENDING: 'border-zinc-300 bg-zinc-50 text-zinc-500',
}

const CONNECTOR_STYLES: Record<string, string> = {
    OK: 'bg-emerald-400',
    ERROR: 'bg-red-400',
    PENDING: 'bg-zinc-300',
}

const STATUS_TEXT: Record<string, string> = {
    OK: 'Concluído',
    ERROR: 'Falhou',
    PENDING: 'Pendente',
}

/** Um "step" por caixa (Registro → OCR → Extração → Validação), ligadas por
 * linhas conectoras — cor por status. Clicar numa caixa seleciona o step
 * (o painel de detalhe é renderizado por quem usa este componente). */
export function ProcessPipelineDiagram({
    steps,
    selectedStepKey,
    onSelectStep,
}: {
    steps: ProcessStep[]
    selectedStepKey: StepKey | null
    onSelectStep: (key: StepKey) => void
}) {
    return (
        <ol className="flex items-center overflow-x-auto py-6" aria-label="Etapas do processamento">
            {steps.map((step, index) => (
                <li key={step.key} className="flex shrink-0 items-center">
                    <button
                        type="button"
                        onClick={() => onSelectStep(step.key)}
                        aria-current={selectedStepKey === step.key ? 'step' : undefined}
                        className={`flex min-w-[120px] flex-col items-center gap-1 rounded-lg border-2 px-4 py-3 text-sm font-medium ${
                            BOX_STYLES[step.status]
                        } ${selectedStepKey === step.key ? 'ring-2 ring-zinc-400 ring-offset-2' : ''}`}
                    >
                        <span>{step.label}</span>
                        <span className="text-xs font-normal opacity-80">{STATUS_TEXT[step.status]}</span>
                    </button>
                    {index < steps.length - 1 ? (
                        <div aria-hidden="true" className={`h-0.5 w-10 ${CONNECTOR_STYLES[step.status]}`} />
                    ) : null}
                </li>
            ))}
        </ol>
    )
}
