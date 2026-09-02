import { STATUS_GROUP_LABELS, STATUS_GROUP_ORDER } from '../types'
import type { ProcessStatusGroup } from '../types'

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
    return (
        <button
            type="button"
            onClick={onClick}
            aria-pressed={active}
            className={`h-8 rounded-full border px-3 text-sm font-medium transition ${
                active
                    ? 'border-zinc-900 bg-zinc-900 text-white'
                    : 'border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-100'
            }`}
        >
            {children}
        </button>
    )
}

/** Chips de filtro por status "de negócio" (multi-seleção). "Todos" limpa a
 * seleção. */
export function ProcessFilters({
    selected,
    onToggle,
    onClear,
}: {
    selected: ProcessStatusGroup[]
    onToggle: (group: ProcessStatusGroup) => void
    onClear: () => void
}) {
    return (
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filtrar por status">
            <Chip active={selected.length === 0} onClick={onClear}>
                Todos
            </Chip>
            {STATUS_GROUP_ORDER.map((group) => (
                <Chip key={group} active={selected.includes(group)} onClick={() => onToggle(group)}>
                    {STATUS_GROUP_LABELS[group]}
                </Chip>
            ))}
        </div>
    )
}
