import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

export function EmptyState({ icon: Icon, text }: { icon: LucideIcon; text: ReactNode }) {
    return (
        <div className="flex min-h-[160px] flex-col items-center justify-center gap-2 px-4 py-8 text-center text-sm text-zinc-500">
            <Icon size={24} aria-hidden="true" />
            <span>{text}</span>
        </div>
    )
}
