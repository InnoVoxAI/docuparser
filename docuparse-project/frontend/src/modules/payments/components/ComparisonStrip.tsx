import { AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import type { Check, CheckTone } from '../compareChecks'

const ICONS = { ok: CheckCircle2, warn: AlertTriangle, info: Info } as const
const TONES: Record<CheckTone, string> = {
    ok: 'text-emerald-700',
    warn: 'text-amber-700',
    info: 'text-zinc-600',
}

/** O que casa, o que diverge e o que ainda não foi lido, antes de o analista decidir. */
export function ComparisonStrip({ checks }: { checks: Check[] }) {
    if (checks.length === 0) return null
    return (
        <ul
            aria-label="Conferência"
            className="grid gap-x-6 gap-y-0.5 border-b border-zinc-200 px-4 py-2 sm:grid-cols-2"
        >
            {checks.map((check) => {
                const Icon = ICONS[check.tone]
                return (
                    <li key={check.id} className="flex items-start gap-2 text-sm">
                        <Icon size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${TONES[check.tone]}`} />
                        <span className="text-zinc-700">
                            <strong className="font-semibold text-zinc-900">{check.label}:</strong> {check.text}
                        </span>
                    </li>
                )
            })}
        </ul>
    )
}
