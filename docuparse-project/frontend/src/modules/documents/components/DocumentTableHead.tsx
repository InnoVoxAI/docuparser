import { useEffect, useRef, type ChangeEvent } from 'react'

function SortIndicator({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
    return active ? (
        <span className="ml-1">{dir === 'asc' ? '↑' : '↓'}</span>
    ) : (
        <span className="ml-1 opacity-30">↕</span>
    )
}

export function DocumentTableHead({
    compact,
    selectable,
    sortKey,
    sortDir,
    onSort,
    allSelected,
    someSelected,
    onToggleAll,
}: {
    compact: boolean
    selectable: boolean
    sortKey: string | null
    sortDir: 'asc' | 'desc'
    onSort: (key: string) => void
    allSelected: boolean
    someSelected: boolean
    onToggleAll: (e: ChangeEvent<HTMLInputElement>) => void
}) {
    const selectAllRef = useRef<HTMLInputElement | null>(null)
    const thClass = 'cursor-pointer select-none px-3 py-2 hover:text-zinc-700'

    useEffect(() => {
        if (selectAllRef.current) {
            selectAllRef.current.indeterminate = someSelected
        }
    }, [someSelected])

    return (
        <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50 text-left text-xs font-semibold uppercase text-zinc-500">
                {selectable ? (
                    <th className="w-8 px-3 py-2" onClick={(e) => e.stopPropagation()}>
                        <input
                            ref={selectAllRef}
                            type="checkbox"
                            checked={allSelected}
                            onChange={onToggleAll}
                            className="h-4 w-4 cursor-pointer rounded border-zinc-300 accent-zinc-700"
                            aria-label="Selecionar todos"
                        />
                    </th>
                ) : null}
                <th className={thClass} onClick={() => onSort('arquivo')}>
                    Arquivo
                    <SortIndicator active={sortKey === 'arquivo'} dir={sortDir} />
                </th>
                <th className={thClass} onClick={() => onSort('status')}>
                    Status
                    <SortIndicator active={sortKey === 'status'} dir={sortDir} />
                </th>
                {compact ? null : (
                    <th className={thClass} onClick={() => onSort('canal')}>
                        Canal
                        <SortIndicator active={sortKey === 'canal'} dir={sortDir} />
                    </th>
                )}
                {compact ? null : (
                    <th className={thClass} onClick={() => onSort('tipo')}>
                        Tipo
                        <SortIndicator active={sortKey === 'tipo'} dir={sortDir} />
                    </th>
                )}
                <th className={thClass} onClick={() => onSort('atualizado')}>
                    Atualizado
                    <SortIndicator active={sortKey === 'atualizado'} dir={sortDir} />
                </th>
                {compact ? null : <th className="px-3 py-2">Decisão em</th>}
                <th className="w-8 px-2 py-2">
                    <span className="sr-only">Ações</span>
                </th>
            </tr>
        </thead>
    )
}
