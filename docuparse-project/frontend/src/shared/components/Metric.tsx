import type { ReactNode } from 'react'

export function Metric({ label, value }: { label: ReactNode; value: ReactNode }) {
    return (
        <div className="rounded-md border border-zinc-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase text-zinc-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold">{value}</div>
        </div>
    )
}
