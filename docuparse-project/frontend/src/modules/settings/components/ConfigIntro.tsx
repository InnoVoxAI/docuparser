import type { ReactNode } from 'react'

export function ConfigIntro({ title, text }: { title: ReactNode; text: ReactNode }) {
    return (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3">
            <div className="text-sm font-semibold text-sky-950">{title}</div>
            <div className="mt-1 text-sm leading-6 text-sky-800">{text}</div>
        </div>
    )
}
