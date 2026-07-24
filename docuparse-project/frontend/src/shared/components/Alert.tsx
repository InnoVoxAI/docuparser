import type { ReactNode } from 'react'

export function Alert({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'error' | 'success' }) {
    const classes =
        tone === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-zinc-200 bg-white text-zinc-600'
    return <div className={`mb-4 rounded-md border px-3 py-2 text-sm ${classes}`}>{children}</div>
}
