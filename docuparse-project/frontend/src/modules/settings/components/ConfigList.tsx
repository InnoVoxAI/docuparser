import type { Key, ReactNode } from 'react'
import { Settings } from 'lucide-react'
import { EmptyState } from '../../../shared/components'

export function ConfigList({
    title,
    items,
    primaryKey,
    secondaryKey,
}: {
    title: ReactNode
    items: Array<Record<string, unknown> & { id: Key }>
    primaryKey: string
    secondaryKey: string
}) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">{title}</div>
            {items.length === 0 ? (
                <EmptyState icon={Settings} text="Nenhuma configuracao cadastrada." />
            ) : (
                <div className="divide-y divide-zinc-100">
                    {items.map((item) => (
                        <div key={item.id} className="px-4 py-3">
                            <div className="text-sm font-medium">{String(item[primaryKey] ?? '')}</div>
                            <div className="mt-1 text-xs text-zinc-500">{String(item[secondaryKey] ?? '')}</div>
                        </div>
                    ))}
                </div>
            )}
        </section>
    )
}
