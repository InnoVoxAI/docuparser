import type { ReactNode } from 'react'

export function HintPanel({
    title,
    items,
    onUse = undefined,
}: {
    title: ReactNode
    items: string[]
    onUse?: (item: string) => void
}) {
    return (
        <aside className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
            <div className="text-sm font-semibold">{title}</div>
            <div className="mt-3 space-y-2">
                {items.map((item) => (
                    <div
                        key={item}
                        className="flex items-start justify-between gap-2 rounded border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-600"
                    >
                        <span>{item}</span>
                        {onUse ? (
                            <button
                                type="button"
                                onClick={() => onUse(item)}
                                className="shrink-0 rounded border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100"
                            >
                                Usar
                            </button>
                        ) : null}
                    </div>
                ))}
            </div>
        </aside>
    )
}
