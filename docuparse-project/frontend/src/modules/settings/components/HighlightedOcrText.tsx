import type { SchemaExample, SchemaField } from '../../../types'
import { renderHighlightedText } from '../utils'

export function HighlightedOcrText({
    text,
    fields,
    examples,
}: {
    text?: string
    fields: SchemaField[]
    examples: SchemaExample[]
}) {
    const highlights = [
        ...fields.map((field) => field.name).filter(Boolean),
        ...examples.map((example) => example.source).filter(Boolean),
    ]

    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">OCR com destaques</div>
            <div className="max-h-[520px] overflow-auto whitespace-pre-wrap px-3 py-3 font-mono text-xs leading-5 text-zinc-700">
                {text ? renderHighlightedText(text, highlights) : 'Selecione um documento com transcricao OCR.'}
            </div>
        </section>
    )
}
