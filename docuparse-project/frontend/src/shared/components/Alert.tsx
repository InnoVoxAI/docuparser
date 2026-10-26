import type { ReactNode } from 'react'

const TONES = {
    neutral: 'border-zinc-200 bg-white text-zinc-600',
    error: 'border-red-200 bg-red-50 text-red-700',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
}

export function Alert({
    children,
    tone = 'neutral',
    className = 'mb-4',
}: {
    children: ReactNode
    tone?: keyof typeof TONES
    className?: string
}) {
    return <div className={`${className} rounded-md border px-3 py-2 text-sm ${TONES[tone]}`}>{children}</div>
}
