export interface StatRow {
    label: string
    value: number
    /** Classe de cor da barra (ex.: 'bg-red-400'). Default: cinza. */
    barClass?: string
}

/** Lista de barras horizontais proporcionais — usada em "por status", "por
 * etapa", "erros por tipo", etc. */
export function StatBreakdown({
    title,
    rows,
    total,
    emptyText = 'Sem dados.',
}: {
    title: string
    rows: StatRow[]
    /** Denominador das barras. Default: maior valor da lista. */
    total?: number
    emptyText?: string
}) {
    const denominator = Math.max(total ?? Math.max(...rows.map((row) => row.value), 0), 1)
    const hasData = rows.some((row) => row.value > 0)

    return (
        <section className="rounded-lg border border-zinc-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-zinc-800">{title}</h2>
            {!hasData ? (
                <p className="mt-3 text-sm text-zinc-500">{emptyText}</p>
            ) : (
                <ul className="mt-3 space-y-2.5">
                    {rows.map((row) => (
                        <li key={row.label} className="text-sm">
                            <div className="flex items-baseline justify-between gap-2">
                                <span className="truncate text-zinc-600">{row.label}</span>
                                <span className="shrink-0 font-semibold tabular-nums text-zinc-900">{row.value}</span>
                            </div>
                            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
                                <div
                                    className={`h-full rounded-full ${row.barClass ?? 'bg-zinc-400'}`}
                                    style={{ width: `${Math.round((row.value / denominator) * 100)}%` }}
                                />
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </section>
    )
}
