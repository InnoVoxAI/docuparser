import type { SchemaExample } from '../../../types'

export function ExamplesEditor({
    examples,
    onChange,
    referenceText,
}: {
    examples: SchemaExample[]
    onChange: (examples: SchemaExample[]) => void
    referenceText?: string
}) {
    const updateExample = (index: number, patch: Partial<SchemaExample>) => {
        onChange(examples.map((example, exampleIndex) => (exampleIndex === index ? { ...example, ...patch } : example)))
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
            <section className="rounded-md border border-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                    <div className="text-sm font-semibold">Few-shot anotados</div>
                    <button
                        type="button"
                        onClick={() => onChange([...examples, { field: '', expected: '', source: '' }])}
                        className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        Adicionar
                    </button>
                </div>
                <div className="divide-y divide-zinc-100">
                    {examples.map((example, index) => (
                        <div key={`${example.field}-${index}`} className="grid gap-2 px-3 py-3 md:grid-cols-3">
                            <input
                                value={example.field}
                                onChange={(event) => updateExample(index, { field: event.target.value })}
                                className="input"
                                placeholder="campo"
                            />
                            <input
                                value={example.expected}
                                onChange={(event) => updateExample(index, { expected: event.target.value })}
                                className="input"
                                placeholder="valor esperado"
                            />
                            <input
                                value={example.source}
                                onChange={(event) => updateExample(index, { source: event.target.value })}
                                className="input"
                                placeholder="trecho fonte"
                            />
                        </div>
                    ))}
                </div>
            </section>
            <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                <div className="text-sm font-semibold">Texto de apoio</div>
                <div className="mt-3 max-h-[260px] overflow-auto whitespace-pre-wrap rounded border border-zinc-200 bg-white p-3 font-mono text-xs text-zinc-600">
                    {referenceText || 'Selecione um documento na aba OCR referencia para copiar trechos fonte.'}
                </div>
            </section>
        </div>
    )
}
