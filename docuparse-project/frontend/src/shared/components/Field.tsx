import type { ReactNode } from 'react'

export function Field({ label, children }: { label: ReactNode; children: ReactNode }) {
    return (
        <label className="block">
            <span className="mb-1 block text-xs font-semibold uppercase text-zinc-500">{label}</span>
            {children}
        </label>
    )
}
