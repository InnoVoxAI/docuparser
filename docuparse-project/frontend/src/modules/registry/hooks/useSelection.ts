import { useState } from 'react'

/** Linhas marcadas para decisão em lote. */
export function useSelection() {
    const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
    return {
        selected,
        toggle: (id: string) =>
            setSelected((current) => {
                const next = new Set(current)
                if (!next.delete(id)) next.add(id)
                return next
            }),
        toggleAll: (ids: string[], checked: boolean) =>
            setSelected((current) => {
                const next = new Set(current)
                ids.forEach((id) => (checked ? next.add(id) : next.delete(id)))
                return next
            }),
        clear: () => setSelected(new Set()),
    }
}
