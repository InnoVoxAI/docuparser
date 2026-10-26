import type { EntityType } from '../schemas/registry'
import { ENTITY_LABELS, REVIEW_TAB_ORDER } from '../utils'

/** Abas na ordem em que se confirma: planos, contas, condomínios. Abas sem pendência ficam discretas. */
export function ReviewTabs({
    active,
    counts,
    onChange,
}: {
    active: EntityType
    counts: Record<string, number>
    onChange: (type: EntityType) => void
}) {
    return (
        <div role="tablist" aria-label="Tipo de cadastro" className="flex flex-wrap gap-1">
            {REVIEW_TAB_ORDER.map((type) => {
                const count = counts[type] ?? 0
                return (
                    <button
                        key={type}
                        role="tab"
                        type="button"
                        aria-selected={active === type}
                        onClick={() => onChange(type)}
                        className={`h-9 rounded-md px-3 text-sm font-medium ${
                            active === type
                                ? 'bg-zinc-900 text-white'
                                : `border border-zinc-300 hover:bg-zinc-100 ${count === 0 ? 'text-zinc-400' : 'text-zinc-700'}`
                        }`}
                    >
                        {ENTITY_LABELS[type]} ({count})
                    </button>
                )
            })}
        </div>
    )
}
