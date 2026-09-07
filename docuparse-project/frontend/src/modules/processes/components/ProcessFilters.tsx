import { STATUS_GROUP_LABELS, STATUS_GROUP_ORDER } from '../types'
import type { ProcessStatusGroup } from '../types'

/** Dropdown de filtro por status "de negócio" — um status por vez, ou "Todos". */
export function ProcessFilters({
    selected,
    onChange,
}: {
    selected: ProcessStatusGroup | ''
    onChange: (group: ProcessStatusGroup | '') => void
}) {
    return (
        <label className="flex flex-col gap-1 text-sm text-zinc-600">
            <span className="font-medium">Status</span>
            <select
                value={selected}
                onChange={(event) => onChange(event.target.value as ProcessStatusGroup | '')}
                className="h-9 rounded-md border border-zinc-300 bg-white px-2 text-sm text-zinc-800 outline-none focus:border-zinc-500"
            >
                <option value="">Todos</option>
                {STATUS_GROUP_ORDER.map((group) => (
                    <option key={group} value={group}>
                        {STATUS_GROUP_LABELS[group]}
                    </option>
                ))}
            </select>
        </label>
    )
}
