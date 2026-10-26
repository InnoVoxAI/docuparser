/** Paginação das propostas (a API entrega em blocos). */
export function ReviewPager({
    offset,
    shown,
    total,
    onChange,
}: {
    offset: number
    shown: number
    total: number
    onChange: (offset: number) => void
}) {
    if (total <= shown && offset === 0) return null
    return (
        <div className="flex items-center justify-between text-sm text-zinc-600">
            <span>
                {offset + 1} a {offset + shown} de {total}
            </span>
            <div className="flex gap-2">
                <button
                    type="button"
                    disabled={offset === 0}
                    onClick={() => onChange(Math.max(offset - shown, 0))}
                    className="h-8 rounded-md border border-zinc-300 px-3 disabled:opacity-50"
                >
                    Anterior
                </button>
                <button
                    type="button"
                    disabled={offset + shown >= total}
                    onClick={() => onChange(offset + shown)}
                    className="h-8 rounded-md border border-zinc-300 px-3 disabled:opacity-50"
                >
                    Próxima
                </button>
            </div>
        </div>
    )
}
