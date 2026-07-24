import { Field } from '../../../shared/components'
import { PROMPT_HINTS } from '../types'
import { HintPanel } from './HintPanel'

export function ExtractionInstructionsTab({
    prompt,
    setPrompt,
}: {
    prompt: string
    setPrompt: (value: string | ((current: string) => string)) => void
}) {
    return (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <Field label="Prompt controlado">
                <textarea
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    className="input min-h-[280px] font-mono"
                />
            </Field>
            <HintPanel
                title="Blocos prontos"
                items={PROMPT_HINTS}
                onUse={(hint) => setPrompt((current) => `${current}\n- ${hint}.`)}
            />
        </div>
    )
}
