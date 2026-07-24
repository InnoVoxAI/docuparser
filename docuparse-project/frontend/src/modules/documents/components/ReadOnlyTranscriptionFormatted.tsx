import { useState } from 'react'

export function ReadOnlyTranscriptionFormatted({ value }: { value?: string }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                <span className="text-sm font-semibold">Transcricao formatada</span>
                <div className="flex items-center gap-2">
                    <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">layout preservado</span>
                    <button
                        type="button"
                        onClick={() => setOpen((o) => !o)}
                        className="text-xs font-medium text-zinc-500 hover:text-zinc-800"
                    >
                        {open ? 'Recolher' : 'Expandir'}
                    </button>
                </div>
            </div>
            <pre
                className={`min-h-[160px] max-h-[420px] w-full overflow-auto whitespace-pre bg-zinc-50 px-3 py-3 text-xs leading-5 text-zinc-700${open ? '' : ' hidden'}`}
            >
                {value || ''}
            </pre>
            {!value ? (
                <div className="px-3 pb-3 text-xs text-zinc-400">
                    Disponivel apenas para PDFs digitais processados pelo engine Docling.
                </div>
            ) : null}
        </div>
    )
}
